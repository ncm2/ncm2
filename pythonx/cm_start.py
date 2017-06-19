# -*- coding: utf-8 -*-

# For debugging
# NVIM_PYTHON_LOG_FILE=nvim.log NVIM_PYTHON_LOG_LEVEL=INFO nvim

import os
import sys
import importlib
from neovim import attach, setup_logging
from cm import getLogger, start_and_run_channel
import atexit
import threading
import platform

logger = getLogger(__name__)

def main():

    channel_type = sys.argv[1]

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

    if channel_type == 'core':
        source_name = 'cm_core'
        modulename = 'cm_core'
        serveraddr = sys.argv[2]
    else:
        source_name = sys.argv[2]
        modulename = sys.argv[3]
        serveraddr = sys.argv[4]

    setup_logging(modulename)

    logger.info("start_channel for %s", modulename)

    # change proccess title
    try:
        import setproctitle
        setproctitle.setproctitle('%s nvim-completion-manager' % modulename)
    except:
        pass

    # Stop Popen from openning console window on Windows system
    if platform.system() == 'Windows':
        try:
            import subprocess
            cls = subprocess.Popen
            class NewPopen(cls):
                def __init__(self, *args, **keys):
                    if 'startupinfo' not in keys:
                        si = subprocess.STARTUPINFO()
                        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                        keys['startupinfo'] = si
                    cls.__init__(self, *args, **keys)
            subprocess.Popen = NewPopen
        except Exception as ex:
            logger.exception('Failed hacking subprocess.Popen for windows platform: %s', ex)

    try:
        start_and_run_channel(channel_type, serveraddr, source_name, modulename)
    except Exception as ex:
        logger.exception('Exception when running %s: %s', modulename, ex)
        exit(1)
    finally:
        # terminate here
        exit(0)

main()

