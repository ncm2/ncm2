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
from cm import cm

logger = logging.getLogger(__name__)

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
        modulename = 'cm.core'
    else:
        modulename = sys.argv[2]

    # setup for the module 
    setup_logging(modulename)
    logger = logging.getLogger(modulename)
    logger.setLevel(get_loglevel())

    logger = logging.getLogger(__name__)
    logger.setLevel(get_loglevel())

    # change proccess title
    try:
        import setproctitle
        setproctitle.setproctitle('nvim-completion-manager %s' % modulename)
    except:
        pass

    try:
        if start_type == 'core':

            from cm import core
            # connect neovim
            nvim = nvim_env()
            handler = core.CoreHandler(nvim)
            logger.info('starting core, enter event loop')
            cm_event_loop('core',logger,nvim,handler)

        elif start_type == 'channel':

            # connect neovim
            nvim = nvim_env()
            m = importlib.import_module(modulename)
            handler = m.Source(nvim)
            logger.info('handler created, entering event loop')
            cm_event_loop('channel',logger,nvim,handler)

    except Exception as ex:
        logger.exception('Exception when running %s: %s', modulename, ex)
        exit(1)
    finally:
        # terminate here
        exit(0)

def nvim_env():
    nvim = attach('stdio')
    # setup pythonx
    pythonxs = nvim.eval('globpath(&rtp,"pythonx")')
    for path in pythonxs.split("\n"):
        if not path:
            continue
        if path not in sys.path:
            sys.path.append(path)
    return nvim


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

