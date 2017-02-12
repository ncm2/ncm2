# -*- coding: utf-8 -*-

# For debugging
# NVIM_PYTHON_LOG_FILE=nvim.log NVIM_PYTHON_LOG_LEVEL=INFO nvim

from cm import cm
# detach=1 for exit vim quickly
cm.register_source(name='cm-gocode',
                   priority=9,
                   abbreviation='Go',
                   scopes=['go'],
                   detach=1)

import os
import re
import logging
from neovim import attach, setup_logging
import re
import subprocess
import logging
from urllib import request
import json

from cm import cm

logger = logging.getLogger(__name__)


class Source:

    def __init__(self,nvim):

        self._nvim = nvim

    def cm_refresh(self,info,ctx,*args):

        lnum = ctx['lnum']
        col = ctx['col']
        typed = ctx['typed']

        kwtyped = re.search(r'[0-9a-zA-Z_]*?$',typed).group(0)
        startcol = col-len(kwtyped)

        src = cm.get_src(ctx)

        # completion pattern
        if (re.search(r'[\w_]{2,}$',typed)
            or re.search(r'\.[\w_]*$',typed)
            ):
            pass
        else:
            return

        # compute offset
        offset = 0
        for i,line in enumerate(src.split("\n")):
            if i+1==lnum:
                offset += col-1
                break
            else:
                # 1 for \n character
                offset += len(line)+1
        # offset = self._nvim.eval('line2byte(line("."))-1+col(".")-1')

        logger.info('src[%s] offset [%s] lnum[%s] col[%s]', src, offset, lnum, col)

        proc = subprocess.Popen(args=['gocode','-f','json','autocomplete','%s' % offset], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        result, errs = proc.communicate(src.encode('utf-8'),timeout=30)
        # result: [1, [{"class": "func", "name": "Print", "type": "func(a ...interface{}) (n int, err error)"}, ...]]
        result = json.loads(result.decode('utf-8')) 
        completions = result[1]
        logger.info('completions %s', completions)

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
        ret = self._nvim.call('cm#complete', info['name'], ctx, startcol, matches)
        logger.info('matches %s, ret %s', matches, ret)

