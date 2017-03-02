# -*- coding: utf-8 -*-

# For debugging
# NVIM_PYTHON_LOG_FILE=nvim.log NVIM_PYTHON_LOG_LEVEL=INFO nvim

from cm import get_src, register_source, get_pos, getLogger

# detach=1 for exit vim quickly
register_source(name='cm-gocode',
                priority=9,
                abbreviation='Go',
                scoping=True,
                scopes=['go'],
                cm_refresh_patterns=[r'\.(\w*)$'],)

import os
import re
import logging
from neovim import attach, setup_logging
import re
import subprocess
import logging
from urllib import request
import json

logger = getLogger(__name__)


class Source:

    def __init__(self,nvim):

        self._nvim = nvim

    def cm_refresh(self,info,ctx,*args):

        src = get_src(self._nvim,ctx)
        # convert lnum, col to offset
        offset = get_pos(ctx['lnum'],ctx['col'],src)

        # invoke gocode
        proc = subprocess.Popen(args=['gocode','-f','json','autocomplete','%s' % offset], 
                                stdin=subprocess.PIPE, 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.DEVNULL)

        result, errs = proc.communicate(src.encode('utf-8'),timeout=30)
        # result: [1, [{"class": "func", "name": "Print", "type": "func(a ...interface{}) (n int, err error)"}, ...]]
        result = json.loads(result.decode('utf-8')) 
        logger.info("result %s", result)
        completions = result[1]

        if not completions:
            return

        matches = []

        for complete in completions:
            
            item = dict(word=complete['name'],
                        icase=1,
                        dup=1,
                        menu=complete.get('type',''),
                        # info=complete.get('doc',''),
                        )
            matches.append(item)

        # cm#complete(src, context, startcol, matches)
        ret = self._nvim.call('cm#complete', info['name'], ctx, ctx['startcol'], matches)
        logger.info('matches %s, ret %s', matches, ret)

