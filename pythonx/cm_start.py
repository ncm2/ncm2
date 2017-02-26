# -*- coding: utf-8 -*-

# For debugging
# NVIM_PYTHON_LOG_FILE=nvim.log NVIM_PYTHON_LOG_LEVEL=INFO nvim

import os
import sys
import re
import importlib
from neovim import attach, setup_logging
import cm

logger = cm.getLogger(__name__)

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

    cm.start_channel(source_name,modulename,addr,start_type)

main()

