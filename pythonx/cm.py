import os
import sys
import importlib
import logging
from neovim.api import Nvim
from neovim import setup_logging, attach

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
        return level

    logger = logging.getLogger(__name__)
    logger.setLevel(get_loglevel())
    return logger

logger = getLogger(__name__)

# python="python2" is only used for sources that depends on python2 libraries,
# don't use it if possible
def register_source(name,abbreviation,priority,enable=True,events=[],detach=0,python='python3',**kwargs):
    # implementation is put inside cm_core
    # 
    # cm_core use a trick to only register the source withou loading the entire
    # module
    return

def context_changed(ctx1,ctx2):
    # same as cm#context_changed
    # return ctx1 is None or ctx2 is None or ctx1['changedtick']!=ctx2['changedtick'] or ctx1['curpos']!=ctx2['curpos']
    # Note: changedtick is triggered when `<c-x><c-u>` is pressed due to vim's
    # bug, use curpos as workaround
    return ctx1 is None or ctx2 is None or ctx1['curpos']!=ctx2['curpos']

def get_src(nvim,ctx):
    """
    :type nvim: Nvim
    """

    bufnr = ctx['bufnr']
    changedtick = ctx['changedtick']

    key = (bufnr,changedtick)
    if key != getattr(get_src,'_cache_key',None):
        lines = nvim.buffers[bufnr][:]
        get_src._cache_src = "\n".join(lines)
        get_src._cache_key = key

    scope_offset = ctx.get('scope_offset',0)
    scope_len = ctx.get('scope_len',len(get_src._cache_src))

    return get_src._cache_src[scope_offset:scope_offset+scope_len]


# convert (lnum, col) to pos
def get_pos(lnum,col,src):

    # curpos
    lines = src.split('\n')
    pos = 0
    for i in range(lnum-1):
        pos += len(lines[i])+1
    pos += col-1

    return pos

def get_lnum_col(pos,src):
    splited = src.split("\n")
    p = 0
    for idx,line in enumerate(splited):
        if p<=pos and p+len(line)>=pos:
            return (idx+1,pos-p+1)
        p += len(line)+1

# allow a source to preprocess inputs before commit to the manager
def get_matcher(nvim):

    if hasattr(get_matcher,'matcher'):
        return get_matcher.matcher

    # from cm.matchers.prifex_matcher import Matcher
    matcher_opt = nvim.eval('g:cm_matcher')
    m = importlib.import_module(matcher_opt['module'])

    def chcmp_smartcase(a,b):
        if a.isupper():
            return a==b
        else:
            return a == b.lower()

    def chcmp_case(a,b):
        return a==b

    def chcmp_icase(a,b):
        return a.lower()==b.lower()

    chcmp = None
    case = matcher_opt.get('case','')
    if case not in ['case','icase','smartcase']:
        ignorecase,sartcase = nvim.eval('[&ignorecase,&smartcase]')
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
    elif case=='smartcase':
        chcmp = chcmp_smartcase

    # cache result
    get_matcher.matcher = m.Matcher(nvim,chcmp)
    return get_matcher.matcher

def start_channel(source_name,modulename,serveraddr,start_type='channel'):

    # setup logging
    setup_logging(modulename)
    # setup logger for module
    logger = getLogger(modulename)

    logger = getLogger(__name__)

    logger.info("start_channel for %s", modulename)

    # change proccess title
    try:
        import setproctitle
        setproctitle.setproctitle('%s nvim-completion-manager' % modulename)
    except:
        pass

    try:

        # connect neovim and setup python environment
        nvim = setup_neovim(serveraddr)

        if start_type == 'core':

            import cm_core
            nvim.vars['_cm_channel_id'] = nvim.channel_id
            handler = cm_core.CoreHandler(nvim)
            logger.info('starting core, enter event loop')
            _cm_event_loop('core',logger,nvim,handler)

        elif start_type == 'channel':

            nvim.call('cm#_channel_started',source_name, nvim.channel_id)

            if sys.version_info.major==2:
                # python2 doesn't support namespace package
                # use load_source as a workaround
                import imp
                file = modulename.replace('.','/')
                exp = 'globpath(&rtp,"pythonx/%s.py",1)' % file
                path = nvim.eval(exp).strip()
                logger.info('python2 file path: %s, exp: %s',path, exp)
                m = imp.load_source(modulename,path)
            else:
                m = importlib.import_module(modulename)

            handler = m.Source(nvim)
            logger.info('handler created, entering event loop')
            _cm_event_loop('channel',logger,nvim,handler)

    except Exception as ex:
        logger.exception('Exception when running %s: %s', modulename, ex)
        exit(1)
    finally:
        # terminate here
        exit(0)

def setup_neovim(serveraddr):

    logger.info("connecting to neovim server: %s",serveraddr)
    # create another connection to avoid synchronization issue?
    if len(serveraddr.split(':'))==2:
        serveraddr,port = serveraddr.split(':')
        port = int(port)
        nvim = attach('tcp',address=serveraddr,port=port)
    else:
        nvim = attach('socket',path=serveraddr)

    # setup pythonx
    pythonxs = nvim.eval('globpath(&rtp,"pythonx",1)')
    for path in pythonxs.split("\n"):
        if not path:
            continue
        if path not in sys.path:
            sys.path.append(path)
    return nvim

def _cm_event_loop(type,logger,nvim,handler):

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


