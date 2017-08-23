import sys
import os
import importlib
import logging
from neovim.api import Nvim
from neovim import attach, setup_logging

def getLogger(name):

    def get_loglevel():
        # logging setup
        level = logging.INFO
        if 'NVIM_PYTHON_LOG_LEVEL' in os.environ:
            l = getattr(logging,
                    os.environ['NVIM_PYTHON_LOG_LEVEL'].strip(),
                    level)
            if isinstance(l, int):
                level = l
        if 'NVIM_NCM_LOG_LEVEL' in os.environ:
            l = getattr(logging,
                    os.environ['NVIM_NCM_LOG_LEVEL'].strip(),
                    level)
            if isinstance(l, int):
                level = l
        return level

    logger = logging.getLogger(__name__)
    logger.setLevel(get_loglevel())
    return logger

logger = getLogger(__name__)

# python="python2" is only used for sources that depends on python2 libraries,
# don't use it if possible
def register_source(name, abbreviation='', priority=5, enable=True, events=[], python='python3', multi_thread=None, **kwargs):
    # implementation is put inside cm_core
    # 
    # cm_core use a trick to only register the source withou loading the entire
    # module
    return


# Base class for cm_core, sources, and scopers
class Base:

    def __init__(self,nvim):

        """
        :type nvim: Nvim
        """

        self.nvim = nvim
        self.logger = getLogger(self.__module__)

    # allow a source to preprocess inputs before committing to the manager
    @property
    def matcher(self):

        nvim = self.nvim

        if not hasattr(self,'_matcher'):

            # from cm.matchers.prifex_matcher import Matcher
            matcher_opt = nvim.eval('g:cm_matcher')
            m = importlib.import_module(matcher_opt['module'])

            chcmp_smartcase = lambda a,b: a==b if a.isupper() else a==b.lower()
            chcmp_case = lambda a,b: a==b
            chcmp_icase = lambda a,b: a.lower()==b.lower()

            case = matcher_opt.get('case','')
            if case not in ['case','icase','smartcase']:
                ignorecase,smartcase = nvim.eval('[&ignorecase,&smartcase]')
                if smartcase:
                    chcmp = chcmp_smartcase
                elif ignorecase:
                    chcmp = chcmp_icase
                else:
                    chcmp = chcmp_case
            elif case=='case':
                chcmp = chcmp_case
            elif case=='icase':
                chcmp = chcmp_icase
            else:
                # smartcase
                chcmp = chcmp_smartcase

            # cache result
            self._matcher = m.Matcher(nvim,chcmp)

        return self._matcher

    def get_pos(self, lnum , col, src):
        """
        convert vim's lnum, col into pos
        """
        lines = src.split('\n')
        pos = 0
        for i in range(lnum-1):
            pos += len(lines[i])+1
        pos += col-1

        return pos

    # convert pos into vim's lnum, col
    def get_lnum_col(self, pos, src):
        """
        convert pos into vim's lnum, col
        """
        splited = src.split("\n")
        p = 0
        for idx,line in enumerate(splited):
            if p<=pos and p+len(line)>=pos:
                return (idx+1,pos-p+1)
            p += len(line)+1

    def get_src(self,ctx):

        """
        Get the source code of current scope identified by the ctx object.
        """

        nvim = self.nvim

        bufnr = ctx['bufnr']
        changedtick = ctx['changedtick']

        key = (bufnr,changedtick)
        if key != getattr(self,'_cache_key',None):
            lines = nvim.buffers[bufnr][:]
            lines.append('') # \n at the end of buffer
            self._cache_src = "\n".join(lines)
            self._cache_key = key

        scope_offset = ctx.get('scope_offset',0)
        scope_len = ctx.get('scope_len',len(self._cache_src))

        return self._cache_src[scope_offset:scope_offset+scope_len]

    def message(self, msgtype, msg):
        self.nvim.call('cm#message', msgtype, msg)

    def complete(self, name, ctx, startcol, matches, refresh=False):
        if isinstance(name,dict):
            name = name['name']
        self.nvim.call('cm#complete', name, ctx, startcol, matches, refresh, async=True)

def setup_neovim(serveraddr):

    logger.info("connecting to neovim server: %s",serveraddr)
    # create another connection to avoid synchronization issue?
    if len(serveraddr.split(':'))==2:
        serveraddr,port = serveraddr.split(':')
        port = int(port)
        nvim = attach('tcp',address=serveraddr,port=port)
    else:
        nvim = attach('socket',path=serveraddr)

    sync_rtp(nvim)
    return nvim

def sync_rtp(nvim):
    """
    sync sys.path with vim's rtp option
    """
    # setup pythonx
    pythonxs = nvim.eval('globpath(&rtp,"pythonx",1)')
    for path in pythonxs.split("\n"):
        if not path:
            continue
        if path not in sys.path:
            sys.path.append(path)
    return nvim

def start_and_run_channel(channel_type, serveraddr, source_name, modulename):

    # connect neovim and setup python environment
    nvim = setup_neovim(serveraddr)

    if channel_type == 'core':

        import cm_core
        handler = cm_core.CoreHandler(nvim)
        logger.info('starting core, enter event loop')

    elif channel_type == 'channel':

        if sys.version_info.major==2:
            # python2 doesn't support namespace package
            # use load_source as a workaround
            import imp
            file = modulename.replace('.','/')
            exp = 'globpath(&rtp,"pythonx/%s.py",1)' % file
            path = nvim.eval(exp).strip()
            logger.info('<%s> python2 file path: %s, exp: %s', source_name, path, exp)
            m = imp.load_source(modulename,path)
            # the previous module load may be hacked before, by register_source
            if not hasattr(m, 'Source'):
                m = imp.reload(m)
        else:
            m = importlib.import_module(modulename)
            # the previous module load may be hacked before, by register_source
            if not hasattr(m, 'Source'):
                m = importlib.reload(m)

        handler = m.Source(nvim)
        nvim.call('cm#_channel_started',source_name, nvim.channel_id, async=True)
        logger.info('<%s> handler created, entering event loop', source_name)


    handler.cm_running_ = False
    handler.cm_msgs_ = []

    def on_request(method, args):
        logger.error('method: %s not implemented, ignore this request', method)

    def on_notification(method, args):

        # A trick to get rid of the greenlet coroutine without using the
        # next_message API.
        handler.cm_msgs_.append( (method,args) )
        if handler.cm_running_:
            logger.info("delay notification handling, method[%s]", method)
            return

        handler.cm_running_ = True

        while handler.cm_msgs_:

            method, args = handler.cm_msgs_.pop(0)

            try:
                logger.debug('%s method: %s, args: %s', channel_type, method, args)

                if channel_type=='channel' and method=='cm_refresh':
                    ctx = args[1]
                    # The refresh calculation may be heavy, and the notification queue
                    # may have outdated refresh events, it would be  meaningless to
                    # process these event
                    if nvim.call('cm#context_changed',ctx):
                        logger.info('context_changed, ignoring context: %s', ctx)
                        continue

                func = getattr(handler,method,None)
                if func is None:
                    logger.info('method: %s not implemented, ignore this message', method)
                    continue

                func(*args)
                logger.debug('%s method %s completed', channel_type, method)
            except Exception as ex:
                logger.exception("Failed processing method: %s, args: %s", method, args)

        handler.cm_running_ = False

    def on_setup():
        on_notification('cm_setup',[])

    try:
        logger.info("<%s> entering event loop", source_name)
        # Use next_message is simpler, as a handler doesn't need to deal with
        # concurrent issue, but it has serious issue,
        # https://github.com/roxma/nvim-completion-manager/issues/35#issuecomment-284049103
        nvim.run_loop(on_request, on_notification, on_setup)
    except Exception as ex:
        logger.exception("nvim.run_loop failed, %s", ex)
    finally:
        # use at_exit to ensure the calling of cm_shutdown
        func = getattr(handler,'cm_shutdown',None)
        if func:
            func()
        if channel_type=='core':
            exit(0)

