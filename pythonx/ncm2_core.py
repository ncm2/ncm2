# -*- coding: utf-8 -*-

import re
import vim
from ncm2 import Ncm2Base, getLogger
import json
import glob
from os import path, environ
from importlib import import_module
from copy import deepcopy, copy
import time
from functools import partial

# don't import this module by other processes
assert environ['NVIM_YARP_MODULE'] == 'ncm2_core'

logger = getLogger(__name__)


class Ncm2Core(Ncm2Base):

    def __init__(self, nvim):

        super().__init__(nvim)

        # { '{source_name}': {'startccol': , 'matches'}
        self._cache_lnum = 0
        self._matches = {}
        self._last_popup = []
        self._notified = {}
        self._subscope_detectors = {}

        self._loaded_plugins = {}

	# LSP based completion source does not has word pattern, use defaults
	# from https://github.com/Microsoft/vscode/blob/2540cbb603f25e5a8f92c8d0657646c77540dfef/src/vs/editor/common/model/wordHelper.ts
	# for default startccol.
	# Read https://github.com/roxma/nvim-completion-manager/issues/30 for more info.
        pats = {}
        pats['*'] = r'(-?\d*\.\d\w*)|([^\`\~\!\@\#\$\%\^\&\*\(\)\-\=\+\[\{\]\}\\\|\;\:\'\"\,\.\<\>\/\?\s]+)'
        pats['css'] = r'(-?\d*\.\d[\w-]*)|([^\`\~\!\@\#\$\%\^\&\*\(\)\=\+\[\{\]\}\\\|\;\:\'\"\,\.\<\>\/\?\s]+)'
        pats['scss'] = pats['css']
        pats['php'] = r'(-?\d*\.\d\w*)|([^\-\`\~\!\@\#\%\^\&\*\(\)\=\+\[\{\]\}\\\|\;\:\'\"\,\.\<\>\/\?\s]+)'
        pats['vim'] = r'(-?\d*\.\d\w*)|([^\-\`\~\!\@\%\^\&\*\(\)\=\+\[\{\]\}\\\|\;\'\"\,\.\<\>\/\?\s]+)'

        # allow @varname $varname :varname
        pats['ruby'] = r'(-?\d*\.\d\w*)|([$:@]?[^\`\~\!\@\#\$\%\^\&\*\(\)\-\=\+\[\{\]\}\\\|\;\:\'\"\,\.\<\>\/\?\s]+)'

        self._word_patterns = pats

    def notify(self, method: str, *args):
        self.nvim.call(method, *args, async_=True)

    def get_word_pattern(self, ctx, sr):
        pat = sr.get('word_pattern', None)
        scope = ctx.get('scope', ctx.get('filetype', '')).lower()

        if type(pat) == dict:
            pat = pat.get(scope, pat.get('*', None))

        if type(pat) == str:
            return pat

        pats = self._word_patterns
        return pats.get(scope, pats['*'])

    def get_filtered_sources(self, data, names=None):
        sources = data['sources']

        if not names:
            names = sources

        whitelist = data['whitelist_for_buffer']
        if whitelist:
            filtered = {}
            for name in whitelist:
                if name in sources and name in names:
                    filtered[name] = sources[name]
            return filtered

        blacklist = data.get('blacklist_for_buffer', [])
        filtered = copy(sources)
        for name in blacklist:
            if name in filtered:
                del filtered[name]

        filtered2 = {}
        for name in filtered.keys():
            if name in names:
                filtered2[name] = sources[name]
        return filtered2

    def load_plugin(self, _, rtp: str):
        self.update_rtp(rtp)

        for d in rtp.split(','):
            for vs in glob.iglob(path.join(d, 'ncm2-plugin/*.vim')):
                if vs in self._loaded_plugins:
                    continue
                self._loaded_plugins[vs] = True
                logger.info('send vimscript plugin %s', vs)
                self.notify('ncm2#_load_vimscript', vs)

            for py in glob.iglob(path.join(d, 'ncm2-plugin/*.py')):
                if py in self._loaded_plugins:
                    continue
                self._loaded_plugins[py] = True
                logger.info('send python plugin %s', py)
                # async_call to get multiple exceptions properly printed
                self.nvim.async_call(partial(self.load_python, _, py))

            dts = glob.glob(path.join(d, 'pythonx/ncm2_subscope_detector/*.py')) + \
                glob.glob(path.join(d, 'python3/ncm2_subscope_detector/*.py'))
            self.load_subscope_detectors(dts)

        self.notify('ncm2#_au_plugin')

    def load_python(self, _, py):
        logger.info('load_python %s', py)
        with open(py, "rb") as f:
            src = f.read()
            exec(compile(src, py, 'exec'), {}, {})

    def load_subscope_detectors(self, paths):
        new_scope = False

        # auto find scopers
        for py in paths:
            if py in self._loaded_plugins:
                continue
            self._loaded_plugins[py] = True

            try:
                mod = path.splitext(path.basename(py))[0]
                mod = "ncm2_subscope_detector.%s" % mod
                m = import_module(mod)
            except Exception as ex:
                logger.exception('importing scoper <%s> failed', py)
                continue

            sd = m.SubscopeDetector(self.nvim)

            for scope in sd.scope:
                if scope not in self._subscope_detectors:
                    self._subscope_detectors[scope] = []
                    new_scope = True

                self._subscope_detectors[scope].append(sd)

            logger.info('subscope detector <%s> for %s', py, sd.scope)

        if not new_scope:
            return

        detectors_sync = {}
        for scope in self._subscope_detectors.keys():
            detectors_sync[scope] = 1

        self.notify('ncm2#_s', 'subscope_detectors', detectors_sync)
        self.notify('ncm2#_hook_for_subscope_detectors')

    def get_context(self, data, name):
        if type(name) is str:
            sr = data['sources'][name]
        else:
            sr = name
            name = sr['name']
        root_ctx = data['context']
        contexts = self.detect_subscopes(data)
        for ctx in contexts:
            ctx = deepcopy(ctx)
            ctx['source'] = name
            ctx['matcher'] = self.matcher_opt_get(data, sr)
            if not self.source_check_scope(sr, ctx, contexts):
                continue
            self.check_patterns(data, sr, ctx)
            ctx['time'] = time.time()
            return ctx

    def on_notify_dated(self, data, _, failed_notifies=[]):
        for ele in failed_notifies:
            name = ele['name']
            ctx = ele['context']
            notified = self._notified
            if name in notified and notified[name] == ctx:
                logger.debug('%s notification is dated', name)
                if name in notified:
                    notified[name]['refresh'] = True

        names = [e['name'] for e in failed_notifies]
        self.do_on_complete(data, 0, names)

    def do_on_complete(self, data, manual=0, names=None):
        root_ctx = data['context']
        root_ctx['manual'] = manual

        self.cache_cleanup_check(root_ctx)

        contexts = self.detect_subscopes(data)

        # do notify_sources_to_refresh
        notifies = []
        warmups = []

        # get the sources that need to be notified
        sources = self.get_filtered_sources(data, names)

        for tmp_ctx in contexts:
            for name, sr in sources.items():

                ctx = deepcopy(tmp_ctx)
                ctx['early_cache'] = False
                ctx['source'] = name
                ctx['matcher'] = self.matcher_opt_get(data, sr)

                if not self.check_source_notify(data, sr, ctx, contexts):
                    continue

                if not sr['ready']:
                    logger.debug('%s is not ready', name)
                    warmups.append(dict(name=name, context=ctx))
                    continue

                self._notified[name] = dict(refresh=False, context=ctx)
                notifies.append(dict(name=name, context=ctx))

        if warmups:
            self.notify('ncm2#_warmup_sources', data['context'], warmups)

        if notifies:
            cur_time = time.time()
            for noti in notifies:
                ctx = noti['context']
                ctx['time'] = cur_time
            self.notify('ncm2#_notify_complete', root_ctx, notifies)
        else:
            logger.debug('notifies is empty')

    def on_complete(self, data, manual, names=None):

        self.do_on_complete(data, manual, names)

        self.matches_update_popup(data)

    def on_warmup(self, data, names):
        warmups = []

        sources = self.get_filtered_sources(data, names)
        names = list(sources.keys())

        contexts = self.detect_subscopes(data)
        for ctx_idx, tmp_ctx in enumerate(contexts):
            for name in names:
                sr = sources[name]

                ctx = deepcopy(tmp_ctx)
                ctx['early_cache'] = False
                ctx['source'] = sr

                if not sr['enable']:
                    continue

                if not self.source_check_scope(sr, ctx, contexts):
                    continue

                warmups.append(dict(name=name, context=ctx))

        self.notify('ncm2#_warmup_sources', data['context'], warmups)

        self.do_on_complete(data, 0, names)

    def check_source_notify(self, data, sr, ctx, contexts):
        name = sr['name']

        cache = self._matches.get(name, None)
        noti = self._notified.get(name, None)

        if not sr['enable']:
            logger.debug('%s is not enabled', name)
            return False

        if not self.source_check_scope(sr, ctx, contexts):
            logger.debug(
                'source_check_scope ignore <%s> for context scope <%s>', name, ctx['scope'])
            return False

        manual_req = ctx.get('manual', 0)
        pattern_ok = self.check_patterns(data, sr, ctx)
        if manual_req == 2:
            pattern_ok = True

        cache_still_apply = False
        cache_is_manual = False
        if cache:
            cctx = cache['context']
            cache_is_kw_typing = self.is_kw_typing(data, sr, cctx, ctx)
            # match_end could by updated in check_patterns
            cache_still_apply = cache_is_kw_typing and cctx['match_end'] == ctx['match_end']
            if cctx['startccol'] == ctx['startccol']:
                cache_is_manual = cctx.get('manual', 0)

        noti_still_apply = False
        noti_is_manual = False
        if noti:
            nctx = noti['context']
            noti_is_kw_typing = self.is_kw_typing(data, sr, nctx, ctx)
            # match_end could by updated in check_patterns
            noti_still_apply = noti_is_kw_typing and nctx['match_end'] == ctx['match_end']
            if nctx['startccol'] == ctx['startccol']:
                noti_is_manual = nctx.get('manual', 0)

        manual = ctx.get('manual', 0) or cache_is_manual or noti_is_manual
        ctx['manual'] = manual

        if not (data['auto_popup'] and sr['auto_popup']) and not manual:
            logger.debug('<%s> is not auto_popup', name)
            return False

        cmplen_ok = False
        cmplen = self.source_get_complete_len(data, sr, manual)
        if cmplen is None or cmplen < 0 or len(ctx['base']) < cmplen:
            cmplen_ok = False
        else:
            cmplen_ok = True

        # check patterns
        if not pattern_ok and not cmplen_ok:
            if cache:
                logger.debug('%s cctx - %s, ctx - %s, manual %s cctx [%s] ctx [%s]', name, cctx['startccol'], ctx['startccol'], manual, cctx['base'], ctx['base'])
            if cache and cctx['startccol'] == ctx['startccol'] and \
                len(cctx['base']) > len(ctx['base']):
                    # disable cache when enough chars are deleted
                    cache['enable'] = False
                    cctx['manual'] = 0
                    if noti:
                        nctx['manual'] = 0

            # auto complete with early_cache and len(ctx['base']) > 0
            if manual or not sr['early_cache'] or not len(ctx['base']):
                logger.debug('<%s> pattern and len not ok, no early cache [%s]',
                        name, ctx['base'])
                return False

            ctx['early_cache'] = True
        elif cache:
            logger.debug('<%s> enable cache', name)
            cache['enable'] = True

        need_refresh = False
        if cache:
            need_refresh = cache['refresh']
            if need_refresh or manual_req:
                # reduce further duplicate notification
                cache['refresh'] = 0
            elif cache_still_apply:
                logger.debug('<%s> was cached, context: %s matches: %s',
                             name, cctx, cache['matches'])
                return False

        # we only notify once for each word
        if noti_still_apply and not manual_req and not need_refresh and \
                not noti['refresh']:
            logger.debug('<%s> has been notified, cache %s', name, cache)
            return False
        return True

    def complete(self, data, sctx, startccol, matches, refresh):
        ctx = data['context']
        self.cache_cleanup_check(ctx)

        name = sctx['source']

        sources = self.get_filtered_sources(data)
        sr = sources.get(name, None)
        if not sr or not sr.get('enable', 1):
            logger.error('%s not found or filtered or disabled', name)
            return

        cache = self._matches.get(name, None)
        if cache and cache['context']['context_id'] > sctx['context_id']:
            logger.debug('%s cache is newer, %s', name, cache)
            return

        # cleanup the notified entry once we get 'ncm2#complete' results
        noti = self._notified.get(name, None)
        if noti and sctx['context_id'] >= noti['context']['context_id']:
            del self._notified[name]

        # be careful when completion matches context is dated
        if sctx['tick'] != ctx['tick']:
            if not self.is_kw_typing(data, sr, sctx, ctx):
                logger.info("[%s] dated is_kw_typing fail, old[%s] cur[%s]",
                            name, sctx['typed'], ctx['typed'])
                return
            else:
                logger.info("[%s] dated is_kw_typing ok, old[%s] cur[%s]",
                            name, sctx['typed'], ctx['typed'])

        # adjust for subscope
        if sctx['lnum'] == 1:
            startccol += sctx.get('scope_ccol', 1) - 1

        # a source uses a matcher that does not support inc_match, in this
        # case, we need refresh=1
        refresh = refresh or not sctx.get('inc_match', 1)

        matches = self.matches_formalize(sctx, matches)

        cache = {}

        cache['startccol'] = startccol
        cache['refresh'] = refresh
        cache['matches'] = matches
        cache['context'] = sctx
        cache['enable'] = not sctx.get('early_cache', False)

        self._matches[name] = cache

        self.matches_update_popup(data)

        if refresh and sctx['tick'] != ctx['tick']:
            self.do_on_complete(data, 0, [name])

    def is_kw_typing(self, data, sr, ctx1, ctx2):
        ctx1 = deepcopy(ctx1)
        ctx2 = deepcopy(ctx2)

        if 'startccol' not in ctx1:
            self.check_word_pattern(data, sr, ctx1)
        if 'startccol' not in ctx2:
            self.check_word_pattern(data, sr, ctx2)

        c1s, c1b = ctx1['startccol'], ctx1['base']
        c2s, c2b = ctx2['startccol'], ctx2['base']
        return c1s == c2s and c1b == c2b[:len(c1b)]

    # InsertEnter, InsertLeave, or lnum changed
    def cache_cleanup(self, *args):
        self._matches = {}
        self._notified = {}
        self._last_popup = []

    def cache_cleanup_check(self, ctx):
        if self._cache_lnum != ctx['lnum']:
            self.cache_cleanup()
            self._cache_lnum = ctx['lnum']

    def detect_subscopes(self, data):
        root_ctx = data['context']
        root_ctx['scope_level'] = 1
        ctx_list = [root_ctx]
        sync_detectors = data['subscope_detectors']
        src = '\n'.join(data['lines'])

        i = 0
        while i < len(ctx_list):
            ctx = ctx_list[i]
            i += 1
            scope = ctx['scope']

            if not sync_detectors.get(scope, False):
                continue

            if not self._subscope_detectors.get(scope, None):
                continue

            for sd in self._subscope_detectors[scope]:
                try:
                    lnum, ccol = ctx['lnum'], ctx['ccol']
                    scope_src = self.get_src(src, ctx)

                    res = sd.detect(lnum, ccol, scope_src)
                    if not res:
                        continue
                    sub = deepcopy(ctx)
                    sub.update(res)

                    # adjust offset to global based and add the new context
                    sub['scope_offset'] += ctx.get('scope_offset', 0)
                    sub['scope_lnum'] += ctx.get('scope_lnum', 1) - 1
                    sub['scope_level'] += 1

                    if sub['lnum'] == 1:
                        sub['typed'] = sub['typed'][sub['scope_ccol'] - 1:]
                        sub['scope_ccol'] += ctx.get('scope_ccol', 1) - 1

                    ctx_list.append(sub)
                    logger.info('new sub context: %s', sub)
                except Exception as ex:
                    logger.exception(
                        "exception on scope processing: %s", ex)

        return ctx_list

    def check_word_pattern(self, data, sr, ctx):
        typed = ctx['typed']
        word_pat = self.get_word_pattern(ctx, sr)

        # remove the last word, check whether the special pattern matches
        # word_removed
        end_word_matched = re.search(word_pat + "$", typed)
        if end_word_matched:
            ctx['base'] = end_word_matched.group()
            ctx['startccol'] = ctx['ccol'] - len(ctx['base'])
            word_removed = typed[:end_word_matched.start()]
        else:
            ctx['base'] = ''
            ctx['startccol'] = ctx['ccol']
            word_removed = typed

        ctx['match_end'] = len(word_removed)
        ctx['word_pattern'] = word_pat

    def check_patterns(self, data, sr, ctx):
        self.check_word_pattern(data, sr, ctx)

        typed = ctx['typed']
        pats = sr.get('complete_pattern', [])
        if type(pats) == str:
            pats = [pats]

        # check source extra patterns
        for pat in pats:
            # use greedy match '.*', to push the match to the last occurance
            # pattern
            if not pat.startswith("^"):
                pat = '.*' + pat

            matched = re.search(pat, typed)
            if matched and matched.end() >= len(typed) - len(ctx['base']):
                ctx['match_end'] = matched.end()
                return True

        return False

    def source_get_complete_len(self, data, sr, manual):
        if manual:
            name = 'manual_complete_length'
        else:
            name = 'complete_length'

        if name in sr:
            return sr[name]

        if manual and 'complete_length' in sr:
            return sr['complete_length']

        cmplen = data[name]
        if type(cmplen) == int:
            return cmplen

        pri = sr['priority']

        # format: [ [ minimal priority, min length ], []]
        val = None
        mxpri = -1
        for e in cmplen:
            if pri >= e[0] and e[0] > mxpri:
                val = e[1]
                mxpri = e[0]
        return val

    def source_check_scope(self, sr, ctx, contexts):
        scope = sr.get('scope', None)
        cur_scope = ctx['scope']
        ctx['scope_match'] = ''
        is_root = ctx['scope_level'] == 1
        if not scope:
            # scope setting is None, means that this is a general purpose
            # completion source, only complete for the root scope
            if is_root:
                # if scope blacklist is defined, return false if a match of the
                # context is found
                for item in sr.get('scope_blacklist', []):
                    for c in contexts:
                        if c['scope'] == item:
                            return False
                return True
            else:
                return False

        for scope in scope:
            if scope == cur_scope:
                ctx['scope_match'] = scope
                if sr['subscope_enable']:
                    return True
                else:
                    return is_root
        return False

    def matches_update_popup(self, data):
        ctx = data['context']

        # sort by priority
        names = self._matches.keys()
        srcs = self.get_filtered_sources(data)
        names = sorted(names, key=lambda x: srcs[x]['priority'], reverse=True)

        ccol = ctx['ccol']

        # basic filtering for matches of each source
        names_with_matches = []
        for name in names:

            sr = srcs.get(name, None)
            if not sr or not sr.get('enable', 1):
                logger.error('%s not found or filtered or disabled', name)
                continue

            cache = self._matches[name]
            cache['filtered_matches'] = []

            if not cache['enable']:
                logger.debug('<%s> is disabled', name)
                continue

            sccol = cache['startccol']
            if sccol > ccol or sccol == 0:
                logger.warn('%s invalid startccol %s', name, sccol)
                continue

            sctx = cache['context']

            if 'prev_context' in cache \
                    and self.is_kw_typing(data, sr, cache['prev_context'], ctx) \
                    and sctx.get('inc_match', 1):
                smat = cache['prev_matches']
            else:
                smat = deepcopy(cache['matches'])

            smat_len0 = len(smat)

            smat = self.matches_filter_by_matcher(data, sr, sctx, sccol, smat)
            cache['prev_context'] = ctx
            cache['prev_matches'] = deepcopy(smat)

            smat = self.matches_filter(data, sr, sctx, sccol, smat)
            cache['filtered_matches'] = smat

            logger.debug('%s matches is filtered %s -> %s -> %s',
                         name, len(cache['matches']), smat_len0, len(smat))

            if not smat:
                continue

            names_with_matches.append(name)

        # additional filtering on inter-source level
        names = self.get_sources_for_popup(data, names_with_matches)

        # merge results of sources, popup_limit
        startccol = ccol
        for name in names:
            sr = srcs[name]
            cache = self._matches[name]
            sccol = cache['startccol']
            filtered_matches = cache['filtered_matches']

            # popup_limit
            popup_limit = sr.get('popup_limit', data['popup_limit'])
            if popup_limit >= 0:
                filtered_matches = filtered_matches[: popup_limit]
                if len(filtered_matches) != len(cache['filtered_matches']):
                    logger.debug('%s matches popup_limit %s -> %s',
                                 name,
                                 len(cache['filtered_matches']),
                                 len(filtered_matches))
                    cache['filtered_matches'] = filtered_matches

            for m in filtered_matches:
                ud = m['user_data']
                mccol = ud.get('startccol', sccol)
                if mccol < startccol:
                    startccol = mccol

        typed = ctx['typed']
        matches = []
        for name in names:

            try:
                sr = srcs[name]
                cache = self._matches[name]
                smat = cache['filtered_matches']
                if not smat:
                    continue

                sccol = cache['startccol']
                for e in smat:
                    ud = e['user_data']
                    mccol = ud.get('startccol', sccol)
                    prefix = typed[startccol-1: mccol-1]
                    dw = self.strdisplaywidth(prefix)
                    space_pad = ' ' * dw

                    e['abbr'] = space_pad + e['abbr']
                    e['word'] = prefix + e['word']
                matches += smat

            except Exception as inst:
                logger.exception(
                    '_refresh_completions process exception: %s', inst)
                continue

        logger.info('popup names: %s, startccol: %s, matches cnt: %s',
                    names, startccol, len(matches))

        matches = self.matches_decorate(data, matches)

        if data['total_popup_limit'] != -1:
            matches = matches[0: data['total_popup_limit']]

        self.matches_do_popup(ctx, startccol, matches)

    def get_sources_for_popup(self, data, names):
        return names

    def matcher_opt_get(self, data, sr):
        opt = self.matcher_opt_formalize(data['matcher'])
        if 'matcher' in sr:
            sopt = self.matcher_opt_formalize(sr['matcher'])
            opt.update(sopt)
        return opt

    def sorter_opt_formalize(self, opt):
        if type(opt) is str:
            return dict(name=opt)
        return deepcopy(opt)

    def sorter_opt_get(self, data, sr):
        gsopt = self.sorter_opt_formalize(data['sorter'])
        ssopt = {}
        if 'sorter' in sr:
            ssopt = self.sorter_opt_formalize(sr['sorter'])
        gsopt.update(ssopt)
        return gsopt

    def sorter_get(self, opt):
        name = opt['name']
        modname = 'ncm2_sorter.' + name
        mod = import_module(modname)
        m = mod.Sorter(**opt)
        return m

    def filter_opt_formalize(self, opts):
        opts = deepcopy(opts)
        if type(opts) is not list:
            opts = [opts]
        ret = []
        for opt in opts:
            if type(opt) is str:
                opt = dict(name=opt)
            ret.append(opt)
        return ret

    def filter_opt_get(self, data, sr):
        opt = sr.get('filter', data['filter'])
        return self.filter_opt_formalize(opt)

    def filter_get(self, opts):
        filts = []
        for opt in opts:
            name = opt['name']
            modname = 'ncm2_filter.' + name
            mod = import_module(modname)
            f = mod.Filter(**opt)
            filts.append(f)

        def handler(data, sr, sctx, sccol, matches):
            for f in filts:
                matches = f(data, sr, sctx, sccol, matches)
            return matches
        return handler

    def matches_filter_by_matcher(self, data, sr, sctx, sccol, matches):
        ctx = data['context']
        typed = ctx['typed']
        matcher = self.matcher_get(sctx)
        tmp = []
        for m in matches:
            ud = m['user_data']
            mccol = ud.get('startccol', sccol)
            base = typed[mccol-1:]
            if matcher(base, m):
                tmp.append(m)
        return tmp

    def matches_filter(self, data, sr, sctx, sccol, matches):
        sorter = self.sorter_get(self.sorter_opt_get(data, sr))
        matches = sorter(matches)

        opt = self.filter_opt_get(data, sr)
        filt = self.filter_get(opt)
        matches = filt(data, sr, sctx, sccol, matches)

        return matches

    def matches_decorate(self, data, matches):
        return self.matches_add_source_mark(data, matches)
        return matches

    def matches_add_source_mark(self, data, matches):
        for e in matches:
            name = e['user_data']['source']
            sr = data['sources'][name]
            tag = sr.get('mark', '')
            if tag == '':
                continue
            e['menu'] = "[%s] %s" % (tag, e['menu'])
        return matches

    def matches_do_popup(self, ctx, startccol, matches):
        # json_encode user_data
        for m in matches:
            # user_data might be string by some custom filter
            ud = m['user_data']
            if type(ud) is dict:
                m['user_data'] = json.dumps(ud)

        popup = [ctx['tick'], startccol, matches]
        if self._last_popup == popup:
            return
        self._last_popup = popup

        # startccol -> startbcol
        typed = ctx['typed']
        startbcol = len(typed[: startccol-1].encode()) + 1

        self.notify('ncm2#_update_matches', ctx, startbcol, matches)


ncm2_core = Ncm2Core(vim)

events = ['on_complete', 'cache_cleanup',
          'complete', 'load_plugin', 'load_python', 'on_warmup', 'ncm2_core']

on_complete = ncm2_core.on_complete
matches_update_popup = ncm2_core.matches_update_popup
cache_cleanup = ncm2_core.cache_cleanup
complete = ncm2_core.complete
load_plugin = ncm2_core.load_plugin
load_python = ncm2_core.load_python
on_warmup = ncm2_core.on_warmup
on_notify_dated = ncm2_core.on_notify_dated
get_context = ncm2_core.get_context

__all__ = events
