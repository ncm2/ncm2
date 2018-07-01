# -*- coding: utf-8 -*-

import copy
import re
import vim
from ncm2 import Ncm2Base, getLogger
import json
import glob
from os import path, environ
from importlib import import_module

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

        pats = {}
        pats['*'] = r'(-?\d*\.\d\w*)|([^\`\~\!\@\#\$\%\^\&\*\(\)\-\=\+\[\{\]\}\\\|\;\:\'\"\,\.\<\>\/\?\s]+)'
        pats['css'] = r'(-?\d*\.\d[\w-]*)|([^\`\~\!\@\#\$\%\^\&\*\(\)\=\+\[\{\]\}\\\|\;\:\'\"\,\.\<\>\/\?\s]+)'
        pats['scss'] = pats['css']
        pats['php'] = r'(-?\d*\.\d\w*)|([^\-\`\~\!\@\#\%\^\&\*\(\)\=\+\[\{\]\}\\\|\;\:\'\"\,\.\<\>\/\?\s]+)'
        pats['vim'] = r'(-?\d*\.\d\w*)|([^\-\`\~\!\@\%\^\&\*\(\)\=\+\[\{\]\}\\\|\;\'\"\,\.\<\>\/\?\s]+)'

        self._word_patterns = pats

        self.notify('ncm2#_core_started')

    def notify(self, method: str, *args):
        self.nvim.call(method, *args, async_=True)

    def word_pattern(self, ctx, sr):
        pat = sr.get('word_pattern', None)
        scope = ctx.get('scope', ctx.get('filetype', '')).lower()

        if type(pat) == dict:
            pat = pat.get(scope, pat.get('*', None))

        if type(pat) == str:
            return pat

        pats = self._word_patterns
        return pats.get(scope, pats['*'])

    def load_plugin(self, _, rtp: str):
        self.update_rtp(rtp)

        for d in rtp.split(','):
            for vs in glob.iglob(path.join(d, 'ncm2-plugin/*.vim')):
                if vs in self._loaded_plugins:
                    continue
                self._loaded_plugins[vs] = True
                logger.info('send vimscript plugin %s', vs)
                self.notify('ncm2#_load_vimscript', vs)

            # travel around to get multiple exceptions displayed by yarp
            # ncm_core -> ncm2#_load_python -> self.load_python
            for py in glob.iglob(path.join(d, 'ncm2-plugin/*.py')):
                if py in self._loaded_plugins:
                    continue
                self._loaded_plugins[py] = True
                logger.info('send python plugin %s', py)
                self.notify('ncm2#_load_python', py)

            dts = glob.glob(path.join(d, 'pythonx/ncm2_subscope_detector/*.py')) + \
                glob.glob(path.join(d, 'python3/ncm2_subscope_detector/*.py'))
            self.load_subscope_detectors(dts)

    def load_python(self, _, py):
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
                mod = os.path.splitext(os.path.basename(py))[0]
                mod = "ncm2_subscope_detector.%s" % mod
                m = importlib.import_module(mod)
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

    def on_complete(self, data, manual, failed_notifies = []):

        for ele in failed_notifies:
            name = ele['name']
            ctx = ele['context']
            notified = self._notified
            if name in notified and notified[name] == ctx:
                logger.debug('%s notification is dated', name)
                del notified[name]

        root_ctx = data['context']
        root_ctx['manual'] = manual

        self.cache_cleanup_check(root_ctx)

        contexts = self.detect_subscopes(data)

        # do notify_sources_to_refresh
        notifies = []

        # get the sources that need to be notified
        for ctx_idx, tmp_ctx in enumerate(contexts):
            for name, sr in data['sources'].items():

                ctx = copy.deepcopy(tmp_ctx)
                ctx['early_cache'] = False
                ctx['source'] = name
                ctx['matcher'] = self.matcher_opt_get(data, sr)
                ctx['sorter'] = self.sorter_opt_get(data, sr)

                if not self.check_source_notify(data, sr, ctx):
                    continue

                notifies.append(dict(name=name, context=ctx))

        if notifies:
            self.notify('ncm2#_notify_sources', root_ctx, notifies)
        else:
            logger.debug('ncm2#_notify_sources argument is empty %s', notifies)
        self.matches_update_popup(data)

    def on_warmup(self, data):
        contexts = self.detect_subscopes(data)

        # do notify_sources_to_refresh
        warmups = []

        # get the sources that need to be notified
        for ctx_idx, tmp_ctx in enumerate(contexts):
            for name, sr in data['sources'].items():

                ctx = copy.deepcopy(tmp_ctx)
                ctx['early_cache'] = False
                ctx['source'] = name

                if not sr['enable']:
                    continue

                if not self.source_check_scope(sr, ctx):
                    continue

                warmups.append(dict(name=name, context=ctx))

        self.notify('ncm2#_warmup_sources', warmups)

    def check_source_notify(self, data, sr, ctx):
        name = sr['name']

        cache = self._matches.get(name, None)

        if not sr['enable']:
            return False

        if not self.source_check_scope(sr, ctx):
            logger.debug(
                'source_check_scope ignore <%s> for context scope <%s>', name, ctx['scope'])
            return False

        manual = ctx['manual']

        if not sr['auto_popup'] and not manual:
            logger.debug('<%s> is not auto_popup', name)
            return False

        # check patterns
        if not self.source_check_patterns(data, sr, ctx):
            if sr['early_cache'] and len(ctx['base']):
                ctx['early_cache'] = True
            else:
                logger.debug(
                    'source_check_patterns failed ignore <%s> base %s', name, ctx['base'])
                if cache:
                    cache['enable'] = False
                return False
        else:
            # enable cached
            if cache:
                logger.debug('<%s> enable cache', name)
                cache['enable'] = True

        if not manual:
            need_refresh = False

            # if there's valid cache
            if cache:
                need_refresh = cache['refresh']
                cc = cache['context']
                if not need_refresh and self.is_kw_type(data, sr, cc, ctx):
                    logger.debug('<%s> was cached, context: %s matches: %s',
                                 name, cc, cache['matches'])
                    return False

            # we only notify once for each word
            noti = self._notified.get(name, None)
            if noti and not need_refresh:
                if self.is_kw_type(data, sr, noti, ctx):
                    logger.debug('<%s> has been notified, cache %s', name, cache)
                    return False

        self._notified[name] = ctx
        return True

    def complete(self, data, ctx, startccol, matches, refresh):
        cur_ctx = data['context']
        self.cache_cleanup_check(cur_ctx)

        name = ctx['source']

        sr = data['sources'].get(name, None)
        if not sr:
            logger.error("invalid completion source name [%s]", name)
            return

        cache = self._matches.get(name, None)
        if cache and cache['context']['reltime'] > ctx['reltime']:
            logger.debug('%s cache is newer, %s', name, cache)
            return

        dated = ctx['dated']

        # be careful when completion matches context is dated
        if dated:
            if not self.is_kw_type(data, sr, ctx, cur_ctx):
                logger.info("[%s] dated is_kw_type fail, old[%s] cur[%s]",
                            name, ctx['typed'], cur_ctx['typed'])
                return
            else:
                logger.info("[%s] dated is_kw_type ok, old[%s] cur[%s]",
                            name, ctx['typed'], cur_ctx['typed'])

        # adjust for subscope
        if ctx['lnum'] == 1:
            startccol += ctx.get('scope_ccol', 1) - 1

        matches = self.matches_formalize(ctx, matches)

        if not cache:
            self._matches[name] = {}
            cache = self._matches[name]

        cache['startccol'] = startccol
        cache['refresh'] = refresh
        cache['matches'] = matches
        cache['context'] = ctx
        cache['enable'] = not ctx.get('early_cache', False)

        self.matches_update_popup(data)

    def is_kw_type(self, data, sr, ctx1, ctx2):
        ctx1 = copy.deepcopy(ctx1)
        ctx2 = copy.deepcopy(ctx2)

        if not self.source_check_patterns(data, sr, ctx1):
            logger.debug('old_ctx source_check_patterns failed')
            return False
        if not self.source_check_patterns(data, sr, ctx2):
            logger.debug('cur_ctx source_check_patterns failed')
            return False

        logger.debug('old ctx [%s] cur ctx [%s]', ctx1, ctx2)
        # startccol is set in self.source_check_patterns
        c1s, c1e, c1b = ctx1['startccol'], ctx1['match_end'], ctx1['base']
        c2s, c2e, c2b = ctx2['startccol'], ctx1['match_end'], ctx2['base']
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
                    sub = copy.deepcopy(ctx)
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

    def source_check_patterns(self, data, sr, ctx):
        pats = sr.get('complete_pattern', [])
        if type(pats) == str:
            pats = [pats]

        typed = ctx['typed']
        word_pat = self.word_pattern(ctx, sr)

        # remove the last word, check whether the special pattern matches
        # word_removed
        end_word_matched = re.search(word_pat + "$", typed)
        if end_word_matched:
            ctx['base'] = end_word_matched.group()
            ctx['startccol'] = ctx['ccol'] - len(ctx['base'])
            word_removed = typed[:end_word_matched.start()]
            word_len = len(ctx['base'])
        else:
            ctx['base'] = ''
            ctx['startccol'] = ctx['ccol']
            word_removed = typed
            word_len = 0

        ctx['match_end'] = len(word_removed)
        ctx['word_pattern'] = self.word_pattern(ctx, sr)

        # check source extra patterns
        for pat in pats:
            # use greedy match '.*', to push the match to the last occurance
            # pattern
            if not pat.startswith("^"):
                pat = '.*' + pat

            matched = re.search(pat, typed)
            if matched and matched.end() >= len(typed) - word_len:
                ctx['match_end'] = matched.end()
                return True

        cmplen = self.source_get_complete_len(data, sr)
        if cmplen is None:
            return False

        return word_len >= cmplen

    def source_get_complete_len(self, data, sr):
        if 'complete_length' in sr:
            return sr['complete_length']

        cmplen = data['complete_length']
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

    def source_check_scope(self, sr, ctx):
        scope = sr.get('scope', None)
        cur_scope = ctx['scope']
        ctx['scope_match'] = ''
        is_root = ctx['scope_level'] == 1
        if not scope:
            # scope setting is None, means that this is a general purpose
            # completion source, only complete for the root scope
            if is_root:
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
        typed = ctx['typed']

        matches = []

        # sort by priority
        names = self._matches.keys()
        srcs = data['sources']
        names = sorted(names, key=lambda x: srcs[x]['priority'], reverse=True)

        ccol = ctx['ccol']
        startccol = ccol

        # basick processing per source
        for name in names:

            try:
                sr = srcs[name]

                cache = self._matches[name]
                cache['filtered_matches'] = []

                if not cache['enable']:
                    logger.debug('<%s> ignore by disabled', name)
                    continue

                sccol = cache['startccol']
                if sccol > ccol or sccol == 0:
                    logger.warn(
                        'ignoring invalid startccol for %s %s', name, sccol)
                    continue

                smat = copy.deepcopy(cache['matches'])
                sctx = cache['context']

                base = typed[sccol - 1:]
                smat = self.matches_filter(data, sr, base, smat)

                cache['filtered_matches'] = smat

                if not smat:
                    continue

                if sccol < startccol:
                    startccol = sccol

            except Exception as inst:
                logger.exception(
                    '_refresh_completions process exception: %s', inst)
                continue

        # merge results of sources
        for name in names:

            try:
                sr = srcs[name]
                cache = self._matches[name]
                sccol = cache['startccol']
                smat = cache['filtered_matches']
                if not smat:
                    continue

                prefix = ctx['typed'][startccol-1: sccol-1]
                dw = self.strdisplaywidth(prefix)
                space_pad = ' ' * dw

                for e in smat:
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

        self.matches_do_popup(ctx, startccol, matches)

    def matcher_opt_get(self, data, sr):
        if 'matcher' in sr:
            return sr['matcher']
        else:
            return data['matcher']

    def sorter_opt_get(self, data, sr):
        if 'sorter' in sr:
            return sr['sorter']
        else:
            return data['sorter']

    def filter_get(self, opts):
        if type(opts) is str:
            opts = [opts]

        filts = []
        for opt in opts:
            fields = opt.split(',')
            name = fields[0]
            args = fields[1:]

            mod = import_module('ncm2_filter.' + name)
            filts.append(mod.Filter(*args))

        def filt(base, matches):
            for fl in filts:
                matches = fl.filter(base, matches)
            return matches

        return filt

    def matches_filter(self, data, sr, base, matches):
        opt = self.matcher_opt_get(data, sr)
        matcher = self.matcher_get(opt)

        tmp = []
        for m in matches:
            if matcher(base, m):
                tmp.append(m)
        matches = tmp

        opt = self.sorter_opt_get(data, sr)
        sorter = self.sorter_get(opt)
        matches = sorter(matches)

        filt = self.filter_get(data['filter'])
        matches = filt(base, matches)

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
            m['user_data'] = json.dumps(m['user_data'])

        popup = [startccol, matches]
        if self._last_popup == popup:
            return
        self._last_popup = popup

        # startccol -> startbcol
        typed = ctx['typed']
        startbcol = len(typed[: startccol-1].encode()) + 1

        self.notify('ncm2#_popup', ctx, startbcol, matches)


ncm2_core = Ncm2Core(vim)

events = ['on_complete', 'cache_cleanup',
          'complete', 'load_plugin', 'load_python', 'on_warmup', 'ncm2_core']

on_complete = ncm2_core.on_complete
cache_cleanup = ncm2_core.cache_cleanup
complete = ncm2_core.complete
load_plugin = ncm2_core.load_plugin
load_python = ncm2_core.load_python
on_warmup = ncm2_core.on_warmup

__all__ = events
