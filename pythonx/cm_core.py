# -*- coding: utf-8 -*-

# For debugging
# NVIM_PYTHON_LOG_FILE=nvim.log NVIM_PYTHON_LOG_LEVEL=INFO nvim

import sys
import os
import re
import copy
import importlib
import cm
import subprocess
import time
import cm_default
import threading
import json

logger = cm.getLogger(__name__)

# use a trick to only register the source withou loading the entire
# module
class CmSkipLoading(Exception):
    pass

class CoreHandler(cm.Base):

    def __init__(self,nvim):

        super().__init__(nvim)

        # process control information on channels
        self._channel_processes = {}
        self._channel_threads = {}

        # { '{source_name}': {'startcol': , 'matches'}
        self._matches = {}
        self._sources = {}
        self._subscope_detectors = {}
        self._last_startcol = 0
        self._last_matches  = []
        # should be True for supporting display menu directly without cm_refresh
        self._has_popped_up  = True
        self._complete_timer = None
        self._last_ctx       = None

        self._loaded_modules = {}

    def cm_setup(self):

        # after all sources are registered, so that all channels will be
        # started the first time cm_start_channels is called
        self.nvim.call('cm#_core_channel_started', self.nvim.channel_id, async=True)

        # load configurations
        self._servername = self.nvim.vars['_cm_servername']
        self._start_py   = self.nvim.vars['_cm_start_py_path']
        self._py3        = self.nvim.vars['_cm_py3']
        self._py2        = self.nvim.eval("get(g:,'python_host_prog','python2')")
        self._complete_delay = self.nvim.vars['cm_complete_popup_delay']
        self._completed_snippet_enable = self.nvim.vars['cm_completed_snippet_enable']
        self._completed_snippet_engine = self.nvim.vars['cm_completed_snippet_engine']
        self._multi_thread = int(self.nvim.vars['cm_multi_threading'])

        self.cm_detect_modules()

    def cm_detect_modules(self):

        cm.sync_rtp(self.nvim)

        self._detect_sources()

        self._load_scopers()

    def _load_scopers(self):

        scoper_paths = self.nvim.eval("globpath(&rtp,'pythonx/cm_scopers/*.py',1)").split("\n")
        # auto find scopers
        for path in scoper_paths:
            if not path:
                continue
            try:
                modulename = os.path.splitext(os.path.basename(path))[0]
                modulename = "cm_scopers.%s" % modulename
                if modulename  in self._loaded_modules:
                    continue

                self._loaded_modules[modulename] = True

                m = importlib.import_module(modulename)

                scoper = m.Scoper(self.nvim)
                for scope in scoper.scopes:
                    if scope not in self._subscope_detectors:
                        self._subscope_detectors[scope] = []
                    self._subscope_detectors[scope].append(scoper)
                    logger.info('scoper <%s> imported for %s', modulename, scope)

            except Exception as ex:
                logger.exception('importing scoper <%s> failed: %s', modulename, ex)

        logger.info('_subscope_detectors: %s', self._subscope_detectors)

    def _detect_sources(self):

        # auto find sources
        sources_paths = self.nvim.eval("globpath(&rtp,'pythonx/cm_sources/*.py',1)").split("\n")
        for path in sources_paths:

            modulename = os.path.splitext(os.path.basename(path))[0]
            modulename = "cm_sources.%s" % modulename

            if modulename  in self._loaded_modules:
                continue

            # use a trick to only register the source withou loading the entire
            # module
            def register_source(name,abbreviation,priority,enable=True,events=[],python='python3',multi_thread=None,**kwargs):

                channel = dict(type=python,
                               module=modulename,
                               events=events)

                if not multi_thread is None:
                    channel['multi_thread'] = multi_thread

                source = {}
                source['channel']      = channel
                source['name']         = name
                source['priority']     = priority
                source['enable']       = enable
                source['abbreviation'] = abbreviation
                for k in kwargs:
                    source[k] = kwargs[k]

                logger.info('registering source: %s',source)
                self.nvim.call('cm#register_source', source, async=True)

                # use a trick to only register the source withou loading the entire
                # module
                raise CmSkipLoading()

            old_handler = cm.register_source
            cm.register_source = register_source
            try:
                # register_source
                m = importlib.import_module(modulename)
            except CmSkipLoading:
                # This is not an error
                logger.info('source <%s> registered', modulename)
            except Exception as ex:
                logger.exception("register_source for %s failed", modulename)
            finally:
                # restore
                cm.register_source = old_handler

    def _is_kw_futher_typing(self,info,oldctx,curctx):

        old_typed = oldctx['typed']
        cur_typed = curctx['typed']

        old_len = len(old_typed)
        cur_len = len(cur_typed)

        if cur_len < old_len:
            return False

        tmp_ctx1 = copy.deepcopy(oldctx)
        tmp_ctx2 = copy.deepcopy(curctx)

        if not self._check_refresh_patterns(info,tmp_ctx1,True):
            logger.debug('oldctx _check_refresh_patterns failed')
            return False
        if not self._check_refresh_patterns(info,tmp_ctx2,True):
            logger.debug('curctx _check_refresh_patterns failed')
            return False

        logger.debug('old ctx [%s] cur ctx [%s]', tmp_ctx1, tmp_ctx2)
        # startcol is set in self._check_refresh_patterns
        return tmp_ctx1['startcol'] == tmp_ctx2['startcol']

    def cm_complete(self,srcs,name,ctx,startcol,matches,refresh,outdated,current_ctx):

        if isinstance(name,dict):
            name = name['name']

        if name not in srcs:
            logger.error("invalid completion source name [%s]", name)
            return

        info = srcs[name]

        # be careful when completion matches context is outdated
        if outdated:
            logger.info("[%s] outdated matches, old typed [%s] cur typed[%s]", name, ctx['typed'], current_ctx['typed'])
            if refresh:
                logger.info("[%s] ignore outdated matching refresh=1", name)
                return
            if not self._is_kw_futher_typing(info,ctx,current_ctx):
                logger.info("[%s] matches is outdated. ignore them.", name)
                return
            logger.info("[%s] matches is outdated by keyword further typing. I'm gonna keep it.", name)

        # adjust for subscope
        if ctx['lnum']==1:
            startcol += ctx.get('scope_col',1)-1

        self._sources = srcs

        try:

            # process the matches early to eliminate unnecessary complete function call
            result = self.process_matches(name,ctx,startcol,matches)
            logger.debug('<%s> preprocessing result startcol: %s matches: %s', name, startcol, result)

            if (not result) and (not self._matches.get(name,{}).get('last_matches',[])):
                # not popping up, ignore this request
                logger.debug('Not popping up, not refreshing for cm_complete by %s, startcol %s', name, startcol)
                return

        finally:

            # storing matches

            if name not in self._matches:
                self._matches[name] = {}

            if len(matches)==0:
                del self._matches[name]
            else:
                complete_info = self._matches[name]
                complete_info['startcol'] = startcol
                complete_info['refresh']  = refresh
                complete_info['matches']  = matches
                complete_info['context']  = ctx
                if outdated and complete_info.get('enable',False):
                    # outdated, but it is keyword further typing, do not
                    # override the already enabled matches
                    complete_info['enable'] = True
                else:
                    complete_info['enable']   = not ctx.get('early_cache',False)

        # wait for _complete_timeout, reduce flashes
        if self._has_popped_up:
            logger.info("update popup for [%s]",name)
            # the ctx in parameter maybe a subctx for completion source, use
            # nvim.call to get the root context
            self._refresh_completions(self.nvim.call('cm#context'))
        else:
            logger.debug("delay popup for [%s]",name)

    def cm_insert_enter(self):
        self._matches = {}
        self._last_matches = []
        self._last_startcol = 0

        # complete timer
        self._last_ctx = None
        if self._complete_timer:
            self._complete_timer.cancel()
            self._complete_timer = None

    def _on_complete_timeout(self,srcs,ctx,*args):
        if self._last_ctx!=ctx:
            logger.warn("_on_complete_timeout triggered, but last_ctx is %s, param ctx is %s", self._last_ctx, ctx)
            return
        if not self._has_popped_up:
            self._refresh_completions(ctx)
            self._has_popped_up = True
        else:
            logger.debug("ignore _on_complete_timeout for self._has_popped_up")

    def cm_refresh(self,srcs,root_ctx,force=0,*args):

        root_ctx['scope'] = root_ctx['filetype']
        root_ctx['force'] = force

        # complete delay timer
        self._last_ctx = root_ctx
        self._has_popped_up = False
        if self._complete_timer:
            self._complete_timer.cancel()
            self._complete_timer = None

        # Note: get_src function asks neovim for data, during which another
        # greenlet coroutine could start or run, calculate this as soon as
        # possible to avoid concurrent issue
        ctx_list = self._get_ctx_list(root_ctx)

        self._sources = srcs

        if force:
            # if this is forcing refresh, clear the cached variable to avoid
            # being filtered by the self._complete function
            self._last_matches = []
            self._last_startcol = 0

        # simple complete done
        if root_ctx['typed'] == '':
            self._matches = {}
        elif re.match(r'\s',root_ctx['typed'][-1]):
            self._matches = {}

        # do notify_sources_to_refresh
        refreshes_calls = []
        refreshes_channels = []

        # get the sources that need to be notified
        for ctx_item in ctx_list:
            for name in srcs:
                ctx = copy.deepcopy(ctx_item)
                ctx['early_cache'] = False
                ctx['force'] = force

                info = srcs[name]
                if not info['enable']:
                    # ignore disabled source
                    continue

                try:

                    if not self._check_scope(ctx,info):
                        logger.debug('_check_scope ignore <%s> for context scope <%s>', name, ctx['scope'])
                        continue

                    if not force and not info['auto_popup']:
                        logger.debug('<%s> is not auto_popup', name)
                        continue

                    # refresh patterns
                    if not self._check_refresh_patterns(info,ctx,force):
                        if not force and info['early_cache'] and self._check_refresh_patterns(info,ctx,True):
                            # early cache
                            ctx['early_cache'] = True
                            logger.debug('<%s> early_caching', name)
                        else:
                            logger.debug('cm_refresh ignore <%s>, force[%s] early_cache[%s]', name, force, info['early_cache'])
                            if name in self._matches:
                                self._matches[name]['enable'] = False
                            continue
                    else:
                        # enable cached
                        if name in self._matches:
                            self._matches[name]['enable'] = True

                    if (
                            (name in self._matches) and 
                            not self._matches[name]['refresh'] and 
                            not force and 
                            self._matches[name]['startcol']==ctx['startcol'] and
                            ctx.get('match_end', '') == self._matches[name]['context'].get('match_end', '')
                        ):
                        logger.debug('<%s> has been cached, <%s> candidates', name, len(self._matches[name]['matches']))
                        continue

                    if 'cm_refresh' in info:
                        refreshes_calls.append(dict(name=name, context=ctx))

                    # start channels on demand here
                    if 'channel' in info:
                        channel = info['channel']
                        if 'id' not in channel:
                            self._start_channel(info)

                    channel = info.get('channel',{})
                    if 'id' in channel:
                        refreshes_channels.append(dict(name=name, id=channel['id'], context=ctx))
                except Exception as ex:
                    logger.exception('cm_refresh exception: %s', ex)
                    continue

        if not refreshes_calls and not refreshes_channels:
            logger.info('not notifying any channels, _refresh_completions now')
            self._refresh_completions(root_ctx)
            self._has_popped_up = True
        else:
            logger.info('notify_sources_to_refresh calls cnt [%s], channels cnt [%s]',len(refreshes_calls),len(refreshes_channels))
            logger.debug('cm#_notify_sources_to_refresh [%s] [%s] [%s]', [e['name'] for e in refreshes_calls], [e['name'] for e in refreshes_channels], root_ctx)
            self.nvim.call('cm#_notify_sources_to_refresh', refreshes_calls, refreshes_channels, root_ctx, async=True)

            # complete delay timer
            def on_timeout():
                self.nvim.async_call(self._on_complete_timeout, srcs, root_ctx)
            self._complete_timer = threading.Timer(float(self._complete_delay)/1000, on_timeout )
            self._complete_timer.start()

    def _get_ctx_list(self,root_ctx):
        ctx_list = [root_ctx,]

        # scoping
        i = 0
        while i<len(ctx_list):
            ctx = ctx_list[i]
            scope = ctx['scope']
            if scope in self._subscope_detectors:
                for detector in self._subscope_detectors[scope]:
                    try:
                        sub_ctx = detector.sub_context(ctx, self.get_src(ctx))
                        if sub_ctx:
                            # adjust offset to global based and add the new
                            # context
                            sub_ctx['scope_offset'] += ctx.get('scope_offset',0)
                            sub_ctx['scope_lnum'] += ctx.get('scope_lnum',1)-1
                            if int(sub_ctx['lnum']) == 1:
                                sub_ctx['typed'] = sub_ctx['typed'][sub_ctx['scope_col']-1:]
                                sub_ctx['scope_col'] += ctx.get('scope_col',1)-1
                                logger.info('adjusting scope_col')
                            ctx_list.append(sub_ctx)
                            logger.info('new sub context: %s', sub_ctx)
                    except Exception as ex:
                        logger.exception("exception on scope processing: %s", ex)

            i += 1

            return ctx_list


    def _check_refresh_patterns(self,info,ctx,force=False):

        # Concept of ctx['match_end']:
        #   for cm_refresh_pattern `\/`, and word pattern `[a-z/]`
        #   foo/bar gets `foo/`
        #   foo/bar/baz gets `foo/bar/`
        # It is useful for trigerring cm_refresh in the middle of a word

        patterns = info.get('cm_refresh_patterns',None)
        typed = ctx['typed']

        word_pattern = info.get('word_pattern', None) or cm_default.word_pattern(ctx)

        # remove the last word, check whether the special pattern matches
        # word_removed
        end_word_matched = re.search(word_pattern + "$",typed)
        if end_word_matched:
            ctx['base']       = end_word_matched.group()
            ctx['startcol']   = ctx['col'] - len(ctx['base'].encode('utf-8'))
            word_removed      = typed[:end_word_matched.start()]
            word_len          = len(ctx['base'])
        else:
            ctx['base']       = ''
            ctx['startcol']   = ctx['col']
            word_removed      = typed
            word_len          = 0

        ctx['match_end'] = len(word_removed)

        # check source extra patterns
        if patterns:
            for pattern in patterns:
                # use greedy match '.*', to push the match to the last occurance
                # pattern
                if not pattern.startswith("^"):
                    pattern = '.*' + pattern

                matched = re.search(pattern, typed)
                if matched and matched.end() >= len(typed)-word_len:
                    ctx['match_end'] = matched.end()
                    return True

        min_len = info['cm_refresh_length']

        # always match
        if min_len==0:
            return True

        if force and word_len>0:
            return True

        if min_len > 0 and word_len >= min_len:
            return True

        return False

    # almost the same as `s:check_scope` in `autoload/cm.vim`
    def _check_scope(self,ctx,info):
        scopes = info.get('scopes',None)
        cur_scope = ctx.get('scope',ctx['filetype'])
        is_root_scope = ( cur_scope==ctx['filetype'] )
        ctx['scope_match'] = ''
        if not scopes:
            # scopes setting is None, means that this is a general purpose
            # completion source, only complete for the root scope
            if is_root_scope:
                return True
            else:
                return False
        for scope in scopes:
            if scope==cur_scope:
                ctx['scope_match'] = scope
                if info.get('scoping',False):
                    return True
                else:
                    return is_root_scope
        return False

    def _refresh_completions(self,ctx):
        """
        Note: This function is called via greenlet coroutine. Be careful, avoid
        using blocking requirest.
        """

        matches = []

        # sort by priority
        names = sorted(self._matches.keys(),key=lambda x: self._sources[x]['priority'], reverse=True)

        if len(names)==0:
            # empty
            logger.info('_refresh_completions names: %s, startcol: %s, matches: %s', names, ctx['col'], [])
            self._complete(ctx, ctx['col'], [])
            return

        col = ctx['col']
        startcol = col

        # basick processing per source
        for name in names:

            try:

                self._matches[name]['last_matches'] = []

                # may be disabled due to early_cache
                if not self._matches[name].get('enable',True):
                    logger.debug('<%s> ignore by disabled', name)
                    continue

                source_startcol = self._matches[name]['startcol']
                if source_startcol>col or source_startcol==0:
                    self._matches[name]['last_matches'] = []
                    logger.error('ignoring invalid startcol for %s %s', name, self._matches[name]['startcol'])
                    continue

                source_matches = self._matches[name]['matches']
                source_matches = self.process_matches(name,ctx,source_startcol,source_matches)

                self._matches[name]['last_matches'] = source_matches

                if not source_matches:
                    continue

                # min non empty source_matches's source_startcol as startcol
                if source_startcol < startcol:
                    startcol = source_startcol

            except Exception as inst:
                logger.exception('_refresh_completions process exception: %s', inst)
                continue

        # merge results of sources
        for name in names:

            try:
                source_startcol = self._matches[name]['startcol']
                source_matches = self._matches[name]['last_matches']
                if not source_matches:
                    continue

                prefix = ctx['typed'][startcol-1 : source_startcol-1]

                for e in source_matches:
                    # do the padding in vimscript to avoid the rpc
                    # overhead of calling strdisplaywidth
                    e['padding'] = prefix
                    if 'abbr' not in e:
                        e['abbr'] = e['word']
                    e['snippet_word'] = e['word']
                    e['word'] = prefix + e['word']

                matches += source_matches

            except Exception as inst:
                logger.exception('_refresh_completions process exception: %s', inst)
                continue

        if not matches:
            startcol=len(ctx['typed']) or 1
        logger.info('_refresh_completions names: %s, startcol: %s, matches cnt: %s', names, startcol, len(matches))
        logger.debug('_refresh_completions names: %s, startcol: %s, matches: %s, source matches: %s', names, startcol, matches, self._matches)
        self._complete(ctx, startcol, matches)

    def process_matches(self,name,ctx,startcol,matches):

        info = self._sources[name]
        abbr = info.get('abbreviation','')

        # formalize datastructure
        formalized = []
        for item in matches:
            e = {}
            if type(item)==type(''):
                e['word'] = item
            else:
                e = copy.deepcopy(item)
            e['icase'] = 1
            formalized.append(e)

        # filtering and sorting
        result = self.matcher.process(info,ctx,startcol,formalized)

        # fix some text
        for e in result:

            if 'menu' not in e:
                if 'info' in e and e['info'] and len(e['info'])<50:
                    if abbr:
                        e['menu'] = "<%s> %s" % (abbr,e['info'])
                    else:
                        e['menu'] = e['info']
                else:
                    # info too long
                    if abbr:
                        e['menu'] = "<%s>" % abbr
            else:
                # e['menu'] = "<%s> %s"  % (self._sources[name]['abbreviation'], e['info'])
                pass

        return result


    def _complete(self, ctx, startcol, matches):
        if not matches and not self._last_matches:
            # no need to fire complete message
            logger.info('matches==0, _last_matches==0, ignore')
            return
        not_changed = 0
        if self._last_startcol==startcol and self._last_matches==matches:
            not_changed = 1
            logger.info('ignore _complete call: self._last_startcol==startcol and self._last_matches==matches')

        # Note: The snippet field will not be kept in v:completed_item.  Use
        # this trick to to hack
        snippets = []
        has_snippets = False
        if self._completed_snippet_enable:
            for m in matches:

                if not m.get('snippet', None) and not m.get('is_snippet', None):
                    continue

                has_snippets = True

                snippet = m.get('snippet', '')

                if 'info' not in m or not m['info']:
                    m['info'] = 'snippet@%s' % len(snippets)
                else:
                    m['info'] += '\nsnippet@%s' % len(snippets)

                if snippet and self._completed_snippet_engine=='neosnippet':
                    # neosnippet does not remove the completed word
                    # make them compatible if possible
                    if snippet[0:len(m['snippet_word'])] == m['snippet_word']:
                        snippet = snippet[len(m['snippet_word']):]

                snippets.append(dict(snippet=snippet, word=m['snippet_word']))

            if has_snippets:
                for m in matches:
                    if 'menu' not in m:
                        m['menu'] = ''
                    if m.get('snippet', None) or m.get('is_snippet', None):
                        # [+] sign indicates that this completion item is
                        # expandable
                        m['menu'] = '[+] ' + m['menu']
                    else:
                        m['menu'] = '[ ] ' + m['menu']

        self.nvim.call('cm#_core_complete', ctx, startcol, matches, not_changed, snippets)
        self._last_matches = matches
        self._last_startcol = startcol


    def _start_channel(self,info):

        if 'channel' not in info:
            logger.error("this source does not use channel: %s", info)
            return

        name         = info['name']
        channel      = info['channel']
        channel_type = channel.get('type','')

        py = ''
        if channel_type=='python3':
            py = self._py3
        elif channel_type=='python2':
            py = self._py2
        else:
            logger.info("Unsupported channel_type [%s]",channel_type)

        if name not in self._channel_processes:
            self._channel_processes[name] = {}
        if name not in self._channel_threads:
            self._channel_threads[name] = {}

        process_info = self._channel_processes[name]
        thread_info = self._channel_threads[name]

        # channel process already started
        if 'proc' in process_info or 'thread' in thread_info:
            return

        if self._multi_thread and channel_type=='python3' and channel.get('multi_thread',1) and sys.version_info.major>=3:
            logger.info("starting <%s> thread channel", name)
            thread_info['thread'] = threading.Thread(
                    target=cm.start_and_run_channel,
                    name=name,
                    args=('channel', self._servername, name, channel['module'])
                    )
            thread_info['thread'].start()
            return

        cmd = [py, self._start_py, 'channel', name, channel['module'], self._servername]

        # has not been started yet, start it now
        logger.info('starting channels for %s: %s',name, cmd)

        proc = subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=sys.stdout,stderr=sys.stderr)
        process_info['pid'] = proc.pid
        process_info['proc'] = proc

        logger.info('source <%s> channel pid: %s', name, proc.pid)

    def cm_shutdown(self):

        # wait for channel-threads' exit
        for name in self._channel_threads:
            tinfo = self._channel_threads[name]
            if 'thread' not in tinfo:
                continue
            try:
                logger.info("join <%s> thread", name)
                tinfo['thread'].join(2)
                logger.info("success join <%s> thread", name)
            except Exception as ex:
                logger.exception("timeout join <%s> thread", name)

        # wait for normal exit
        time.sleep(1)

        procs = []
        for name in self._channel_processes:
            pinfo = self._channel_processes[name]
            if 'proc' not in pinfo:
                continue
            proc = pinfo['proc']
            try:
                if proc.poll() is not None:
                    logger.info("channel %s already terminated", name)
                    continue
                procs.append((name,proc))
                logger.info("terminating channel %s", name)
                proc.terminate()
            except Exception as ex:
                logger.exception("send terminate signal failed for %s", name)

        if not procs:
            return

        # wait for terminated
        time.sleep(1)

        # kill all
        for name,proc in procs:
            try:
                if proc.poll() is not None:
                    logger.info("channel %s has terminated", name)
                    continue
                logger.info("killing channel %s", name)
                proc.kill()
                logger.info("hannel %s killed", name)
            except Exception as ex:
                logger.exception("send kill signal failed for %s", name)

    def cm_start_channels(self,srcs,ctx):

        names = sorted(srcs.keys(),key=lambda n: srcs[n]['priority'], reverse=True)
        for name in names:

            info = srcs[name]

            if not info['enable']:
                continue

            # this source is not using channel
            if 'channel' not in info:
                continue

            # channel already started
            if info['channel'].get('id',None):
                continue

            if not self._check_scope(ctx,info):
                continue

            self._start_channel(info)

