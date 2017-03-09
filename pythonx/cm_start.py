# -*- coding: utf-8 -*-

# For debugging
# NVIM_PYTHON_LOG_FILE=nvim.log NVIM_PYTHON_LOG_LEVEL=INFO nvim

import os
import sys
import importlib
from neovim import attach, setup_logging
from cm import getLogger
import atexit

logger = getLogger(__name__)

def main():

    start_type = sys.argv[1]

    # the default nice is inheriting from parent neovim process.  Increment it
    # so that heavy calculation will not block the ui.
    try:
        os.nice(5)
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
        source_name = ''
        modulename = 'cm_core'
        addr = sys.argv[2]
    else:
        source_name = sys.argv[2]
        modulename = sys.argv[3]
        addr = sys.argv[4]

    start_channel(source_name,modulename,addr,start_type)

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
            handler = cm_core.CoreHandler(nvim)
            logger.info('starting core, enter event loop')
            run_event_loop('core',logger,nvim,handler)

        elif start_type == 'channel':

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
            nvim.call('cm#_channel_started',source_name, nvim.channel_id, async=True)
            logger.info('handler created, entering event loop')
            run_event_loop('channel',logger,nvim,handler)

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

def run_event_loop(type,logger,nvim,handler):

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
                logger.debug('%s method: %s, args: %s', type, method, args)

                if type=='channel' and method=='cm_refresh':
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
                logger.debug('%s method %s completed', type, method)
            except Exception as ex:
                logger.exception("Failed processing method: %s, args: %s", method, args)

        handler.cm_running_ = False

    def on_setup():
        on_notification('cm_setup',[])

    # use at_exit to ensure the calling of cm_shutdown
    func = getattr(handler,'cm_shutdown',None)
    if func:
        atexit.register(func)

    # Use next_message is simpler, as a handler doesn't need to deal with
    # concurrent issue, but it has serious issue,
    # https://github.com/roxma/nvim-completion-manager/issues/35#issuecomment-284049103
    nvim.run_loop(on_request, on_notification, on_setup)

main()

