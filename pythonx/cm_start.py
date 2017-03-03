# -*- coding: utf-8 -*-

# For debugging
# NVIM_PYTHON_LOG_FILE=nvim.log NVIM_PYTHON_LOG_LEVEL=INFO nvim

import os
import sys
import re
import importlib
from neovim import attach, setup_logging
from cm import getLogger
import atexit
import greenlet

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
            nvim.vars['_cm_channel_id'] = nvim.channel_id
            handler = cm_core.CoreHandler(nvim)
            logger.info('starting core, enter event loop')
            run_event_loop('core',logger,nvim,handler)

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

    # greenlet.

    def on_setup():
        logger.info('on_setup')

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

    # use at_exit to ensure the calling of cm_shutdown
    func = getattr(handler,'cm_shutdown',None)
    if func:
        atexit.register(func)

    while True:
        msg = nvim.next_message()
        if not msg:
            break
        if msg[0] != 'notification':
            logger.error('unrecognized message: %s', msg)
            continue
        method = ''
        try:
            method = msg[1]
            on_notification(method,msg[2])
        except Exception as ex:
            logger.exception("Error processing notification <%s>, msg: ", msg)
    # nvim.run_loop(on_request, on_notification, on_setup)

main()

