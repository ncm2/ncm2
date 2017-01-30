# -*- coding: utf-8 -*-

# For debugging
# NVIM_PYTHON_LOG_FILE=nvim.log NVIM_PYTHON_LOG_LEVEL=INFO nvim

import os
import re
import logging
from neovim import attach, setup_logging
import re
import subprocess
import logging
from urllib import request
import json

import cm_utils

logger = logging.getLogger(__name__)


class Handler:

    def __init__(self,nvim):

        self._nvim = nvim

    def cm_refresh(self,info,ctx,*args):

        lnum = ctx['lnum']
        col = ctx['col']
        typed = ctx['typed']

        kwtyped = re.search(r'[0-9a-zA-Z_]*?$',typed).group(0)
        startcol = col-len(kwtyped)

        path, filetype = self._nvim.eval('[expand("%:p"),&filetype]')
        if filetype not in ['go','golang','markdown']:
            logger.info('ignore filetype: %s', filetype)
            return

        src = "\n".join(self._nvim.current.buffer[:])

        # completion pattern
        if (re.search(r'[\w_]{2,}$',typed)
            or re.search(r'\.[\w_]*$',typed)
            ):
            pass
        else:
            return


        if filetype=='markdown':
            # setup completions for markdown file
            result = cm_utils.check_markdown_code_block(src,['go','golang'],lnum,col)
            logger.info('try markdown, %s,%s,%s, result: %s', src, col, col, result)
            if result is None:
                return
            src = result['src']
            col = result['col']
            lnum = result['lnum']
            offset = result['pos']
        else:
            offset = self._nvim.eval('line2byte(line("."))-1+col(".")-1')

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

