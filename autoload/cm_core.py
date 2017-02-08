# -*- coding: utf-8 -*-

# For debugging
# NVIM_PYTHON_LOG_FILE=nvim.log NVIM_PYTHON_LOG_LEVEL=INFO nvim

import os
import sys
import re
import logging
import copy
import importlib
import threading
from threading import Thread, RLock
import urllib
import json
from neovim import attach, setup_logging
from http.server import BaseHTTPRequestHandler, HTTPServer
import cm

logger = logging.getLogger(__name__)


class Handler:

    def __init__(self,nvim):
        self._nvim = nvim

        # { '{source_name}': {'startcol': , 'matches'}
        self._matches = {}
        self._sources = {}
        self._last_matches = []
        self._has_popped_up = False
        self._subscope_detectors = {}
        # builtin detectors
        self._subscope_detectors['markdown'] = [cm.MarkdownScope(),]
        htmlScope = cm.HtmlScope()
        self._subscope_detectors['html'] = [htmlScope,]
        self._subscope_detectors['php'] = [htmlScope,]
        self._subscope_detectors['blade'] = [htmlScope,]
        self._subscope_detectors['jinja'] = [htmlScope,]
        self._subscope_detectors['jinja2'] = [htmlScope,]

        self._file_server = FileServer()
        self._file_server.start(self._nvim.eval('v:servername'))

    def cm_complete(self,srcs,name,ctx,startcol,matches,*args):

        self._sources = srcs

        try:

            # process the matches early to eliminate unnecessary complete function call
            result = self.process_matches(name,ctx,startcol,matches)

            if (not result) and (not self._matches.get(name,{}).get('last_matches',[])):
                # not popping up, ignore this request
                logger.info('Not popping up, not refreshing for cm_complete by %s, startcol %s', name, startcol)
                return

        finally:

            # storing matches

            if name not in self._matches:
                self._matches[name] = {}

            if len(matches)==0:
                del self._matches[name]
            else:
                self._matches[name]['startcol'] = startcol
                self._matches[name]['matches'] = matches

        # wait for cm_complete_timeout, reduce flashes
        if self._has_popped_up:
            self._refresh_completions(ctx)

    def cm_insert_enter(self):
        self._matches = {}

    def cm_complete_timeout(self,srcs,ctx,*args):
        if not self._has_popped_up:
            self._refresh_completions(ctx)
            self._has_popped_up = True

    # The completion core itself
    def cm_refresh(self,srcs,root_ctx,*args):

        # update file server
        self._file_server.set_current_ctx(root_ctx)

        # initial scope
        root_ctx['scope'] = root_ctx['filetype']

        self._sources = srcs
        self._has_popped_up = False

        # simple complete done
        if root_ctx['typed'] == '':
            self._matches = {}
        elif re.match(r'[^0-9a-zA-Z_]',root_ctx['typed'][-1]):
            self._matches = {}

        root_ctx['src_uri'] = self._file_server.get_src_uri(root_ctx)
        ctx_lists = [root_ctx,]

        # scoping
        i = 0
        while i<len(ctx_lists):
            ctx = ctx_lists[i]
            scope = ctx['scope']
            if scope in self._subscope_detectors:
                for detector in self._subscope_detectors[scope]:
                    try:
                        sub_ctx = detector.get_subscope_ctx(ctx, self._file_server.get_src(ctx))
                        if sub_ctx:
                            # append the subscope for further processing
                            sub_ctx['scope_offset'] += ctx.get('scope_offset',0)
                            sub_ctx['src_uri'] = self._file_server.get_src_uri(sub_ctx)
                            ctx_lists.append(sub_ctx)
                            logger.info('new sub context: %s', sub_ctx)
                    except Exception as ex:
                        logger.exception("exception on scope processing: %s", ex)

            i += 1

        # do notify_sources_to_refresh
        refreshes_calls = []
        refreshes_channels = []

        for ctx in ctx_lists:
            for name in srcs:
                info = srcs[name]
                try:

                    if not self._check_scope(ctx,info):
                        logger.info('_check_scope ignore <%s> for context scope <%s>', name, ctx['scope'])
                        continue

                    if (info['name'] in self._matches) and (info.get('refresh',0)==0):
                        # no need to refresh
                        continue

                    if 'cm_refresh' in info:
                        # check patterns when necessary
                        if self._check_patterns(ctx['typed'],info['cm_refresh']):
                            refreshes_calls.append(dict(name=name,context=ctx))

                    # start channels on demand here
                    if info.get('channels',None):
                        channel = info['channels'][0]
                        if 'id' not in channel:
                            if channel.get('has_terminated',0)==0:
                                logger.info('starting channels for %s',name)
                                # has not been started yet, start it now
                                info = self._nvim.call('cm#_start_channels',name)

                    for channel in info.get('channels',[]):
                        if 'id' in channel:
                            refreshes_channels.append(dict(name=name,id=channel['id'],context=ctx))
                except Exception as inst:
                    logger.exception('cm_refresh process exception: %s', inst)
                    continue

        if not refreshes_calls and not refreshes_channels:
            logger.info('not notifying any channels, _refresh_completions now')
            self._refresh_completions(root_ctx)
            self._has_popped_up = True
        else:
            logger.info('notify_sources_to_refresh calls cnt [%s], channels cnt [%s]',len(refreshes_calls),len(refreshes_channels))
            logger.debug('cm#_notify_sources_to_refresh [%s] [%s] [%s]', refreshes_calls, refreshes_channels, root_ctx)
            self._nvim.call('cm#_notify_sources_to_refresh', refreshes_calls, refreshes_channels, root_ctx)

    # check patterns for dict, if non dict, return True
    def _check_patterns(self,typed,opt):
        if type(opt)!=type({}):
            return True
        patterns = opt.get('patterns',None)
        if patterns is None:
            return True
        for pattern in patterns:
            if re.search(pattern,typed):
                return True
        return False

    # almost the same as `s:check_scope` in `autoload/cm.vim`
    def _check_scope(self,ctx,info):
        scopes = info.get('scopes',['*'])
        cur_scope = ctx.get('scope',ctx['filetype'])
        for scope in scopes:
            # only match filetype for `*` scope, to prevent multiple notification
            if scope=='*' and cur_scope==ctx['filetype']:
                return True
            if scope==cur_scope:
                return True
        return False

    def _refresh_completions(self,ctx):

        matches = []

        # sort by priority
        names = sorted(self._matches.keys(),key=lambda x: self._sources[x]['priority'], reverse=True)

        if len(names)==0:
            # empty
            logger.info('_refresh_completions names: %s, startcol: %s, matches: %s', names, ctx['col'], [])
            self._complete(ctx, ctx['col'], [])
            return

        startcol = ctx['col']
        base = ctx['typed'][startcol-1:]

        # basick processing per source
        for name in names:

            try:
                source_startcol = self._matches[name]['startcol']
                if source_startcol>ctx['col']:
                    self._matches[name]['last_matches'] = []
                    logger.error('ignoring invalid startcol: %s', self._matches[name])
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

        # merge processing results of sources
        for name in names:

            try:
                source_startcol = self._matches[name]['startcol']
                if source_startcol>ctx['col']:
                    logger.error('ignoring invalid startcol: %s', self._matches[name])
                    continue
                source_matches = self._matches[name]['last_matches']
                prefix = ctx['typed'][startcol-1 : source_startcol-1]

                for e in source_matches:
                    e['word'] = prefix + e['word']
                    # if 'abbr' in e:
                    #     e['abbr'] = prefix + e['abbr']

                matches += source_matches

            except Exception as inst:
                logger.exception('_refresh_completions process exception: %s', inst)
                continue

        logger.info('_refresh_completions names: %s, startcol: %s, matches cnt: %s', names, startcol, len(matches))
        logger.debug('_refresh_completions names: %s, startcol: %s, matches: %s, source matches: %s', names, startcol, matches, self._matches)
        self._complete(ctx, startcol, matches)

    def process_matches(self,name,ctx,startcol,matches):

        # do some basic filtering and sorting
        result = []
        base = ctx['typed'][startcol-1:]

        for item in matches:

            e = {}
            if type(item)==type(''):
                e['word'] = item
            else:
                e = copy.deepcopy(item)

            if 'menu' not in e:
                if 'info' in e and e['info'] and len(e['info'])<70:
                    if self._sources[name].get('abbreviation',''):
                        e['menu'] = self._sources[name]['abbreviation'] + " :" + e['info']
                    else:
                        e['menu'] = e['info']
                else:
                    e['menu'] = self._sources[name].get('abbreviation','')

            if len(base)>len(e['word']):
                continue

            # For now, do the simple smart case filtering
            # TODO: enable custom config
            skip = False
            for a,b in zip(base,e['word']):
                if a.isupper() :
                    if a!=b:
                        skip=True
                        break
                elif a!=b.lower():
                    skip=True
                    break

            if skip:
                continue


            if base.lower() != e['word'][0:len(base)].lower():
                continue

            result.append(e)

        # for now, simply sort them by length
        # TODO: enable custom config
        # in python, 'A' sort's before 'a', we need to swapcase for the 'a'
        # sorting before 'A'
        result.sort(key=lambda e: ( len(e['word']), e['word'].swapcase() ) )

        return result


    def _complete(self, ctx, startcol, matches):
        if len(matches)==0 and len(self._last_matches)==0:
            # no need to fire complete message
            return
        self._nvim.call('cm#_core_complete', ctx, startcol, matches, async=True)

    def cm_shutdown(self):
        self._file_server.shutdown(wait=False)


# Cached file content in memory, and use http protocol to serve files, instead
# of asking vim for file every time.  FileServer is important in implementing
# the scoping feature, for example, language specific completion inside
# markdown code fences.
class FileServer(Thread):

    def __init__(self):
        self._rlock = RLock()
        self._current_context = None
        self._cache_context = None
        self._cache_src = ""
        Thread.__init__(self)

    def start(self,nvim_server_name):
        """
        Start the file server
        @type request: str
        """

        server = self

        class HttpHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                try:
                    server.run_GET(self)
                except Exception as ex:
                    logger.exception('exception on FileServer: %s', ex)
                    self.send_response(500)
                    self.send_header('Content-type','text/html')
                    self.end_headers()
                    message = str(ex)
                    self.wfile.write(bytes(message, "utf8"))

        # create another connection to avoid synchronization issue?
        self._nvim = attach('socket',path=nvim_server_name)

        # Server settings
        # 0 for random port
        server_address = ('127.0.0.1', 0)
        self._httpd = HTTPServer(server_address, HttpHandler)

        Thread.start(self)

    def run_GET(self,request):
        """
        Process get request. This method, with the `run_` prefix is running on
        the same thread as `self.run` method.
        @type request: BaseHTTPRequestHandler
        """

        params = {}
        for e in urllib.parse.parse_qsl(urllib.parse.urlparse(request.path).query):
            params[e[0]] = e[1]
        
        logger.info('thread %s processing %s', threading.get_ident(), params)

        context = json.loads(params['context'])
        src = self.get_src(context)
        if src is None:
            src = ""

        request.send_response(200)
        request.send_header('Content-type','text/html')
        request.end_headers()
        request.wfile.write(bytes(src, "utf8"))

    def run(self):
        logger.info('running server on port %s, thread %s', self._httpd.server_port, threading.get_ident())
        self._httpd.serve_forever()

    def get_src(self,context):

        with self._rlock:

            # If context does not match current context, check the neovim current
            # context, if does not match neither, return None
            if self._context_changed(self._current_context,context):
                self._current_context = self._nvim.eval('cm#context()')
            if self._context_changed(self._current_context,context):
                logger.info('get_src returning None for oudated context: %s', context)
                return None

            # update cache when necessary
            if self._context_changed(self._current_context, self._cache_context):
                logger.info('get_src updating cache for context %s', context)
                self._cache_context = self._current_context
                self._cache_src = "\n".join(self._nvim.current.buffer[:])

            scope_offset = context.get('scope_offset',0)
            scope_len = context.get('scope_len',len(self._cache_src))
            return self._cache_src[scope_offset:scope_offset+scope_len]

    # same as cm#context_changed
    def _context_changed(self,ctx1,ctx2):
        return ctx1 is None or ctx2 is None or ctx1['changedtick']!=ctx2['changedtick'] or ctx1['curpos']!=ctx2['curpos']

    def set_current_ctx(self,context):
        """
        This method is running on main thread as cm core
        """
        with self._rlock:
            self._current_context = context

    def get_src_uri(self,context):
        # changedtick and curpos is enough for outdating check
        stripped = dict(changedtick=context['changedtick'],curpos=context['curpos'])
        if 'scope_offset' in context:
            stripped['scope_offset'] = context['scope_offset']
        if 'scope_len' in context:
            stripped['scope_len'] = context['scope_len']
        query = urllib.parse.urlencode(dict(context=json.dumps(stripped)))
        return urllib.parse.urljoin('http://127.0.0.1:%s' % self._httpd.server_port, '?%s' % query)

    def shutdown(self,wait=True):
        """
        Shutdown the file server
        """
        self._httpd.shutdown()
        if wait:
            self.join()


def main():

    start_type = sys.argv[1]

    # the default nice is inheriting from parent neovim process.  Increment it
    # so that heavy calculation will not block the ui.
    try:
        os.nice(1)
    except:
        pass

    # psutil ionice
    try:
        import psutil
        p = psutil.Process(os.getpid())
        p.ionice(psutil.IOPRIO_CLASS_IDLE)
    except:
        pass

    if start_type == 'core':

        # use the module name here
        setup_logging('cm_core')
        logger = logging.getLogger(__name__)
        logger.setLevel(get_loglevel())

        # change proccess title
        try:
            import setproctitle
            setproctitle.setproctitle('nvim-completion-manager core')
        except:
            pass

        try:
            # connect neovim
            nvim = attach('stdio')
            handler = Handler(nvim)
            logger.info('starting core, enter event loop')
            cm_event_loop('core',logger,nvim,handler)
        except Exception as ex:
            logger.exception('Exception when running channel: %s',ex)
            exit(1)
        finally:
            # terminate here
            exit(0)

    elif start_type == 'channel':

        path = sys.argv[2]
        dir = os.path.dirname(path)
        name = os.path.splitext(os.path.basename(path))[0]

        # use the module name here
        setup_logging(name)
        logger = logging.getLogger(name)
        logger.setLevel(get_loglevel())

        # change proccess title
        try:
            import setproctitle
            setproctitle.setproctitle('nvim-completion-manager %s' % name)
        except:
            pass


        try:
            # connect neovim
            nvim = attach('stdio')
            sys.path.append(dir)
            m = importlib.import_module(name)
            handler = m.Handler(nvim)
            logger.info('handler created, entering event loop')
            cm_event_loop('channel',logger,nvim,handler)
        except Exception as ex:
            logger.exception('Exception: %s',ex)
            exit(1)
        finally:
            # terminate here
            exit(0)

def get_loglevel():
    # logging setup
    level = logging.INFO
    if 'NVIM_PYTHON_LOG_LEVEL' in os.environ:
        l = getattr(logging,
                os.environ['NVIM_PYTHON_LOG_LEVEL'].strip(),
                level)
        if isinstance(l, int):
            level = l
    return level


def cm_event_loop(type,logger,nvim,handler):

    def on_setup():
        logger.info('on_setup')

    def on_request(method, args):

        func = getattr(handler,method,None)
        if func is None:
            logger.info('method: %s not implemented, ignore this request', method)
            return None

        func(*args)

    def on_notification(method, args):
        logger.debug('%s method: %s, args: %s', type, method, args)

        if type=='channel' and method=='cm_refresh':
            ctx = args[1]
            # The refresh calculation may be heavy, and the notification queue
            # may have outdated refresh events, it would be  meaningless to
            # process these event
            if nvim.call('cm#context_changed',ctx):
                logger.info('context_changed, ignoring context: %s', ctx)
                return

        func = getattr(handler,method,None)
        if func is None:
            logger.info('method: %s not implemented, ignore this message', method)
            return

        func(*args)

        logger.debug('%s method %s completed', type, method)

    nvim.run_loop(on_request, on_notification, on_setup)

    # shutdown
    func = getattr(handler,'cm_shutdown',None)
    if func:
        func()


main()

