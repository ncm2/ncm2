# -*- coding: utf-8 -*-

# For debugging
# NVIM_PYTHON_LOG_FILE=nvim.log NVIM_PYTHON_LOG_LEVEL=INFO nvim

import os
import re
import logging
import jedi
from neovim import attach, setup_logging
import cm_utils

logger = logging.getLogger(__name__)

class Handler:

    def __init__(self,nvim):

        self._nvim = nvim

    def cm_event(self,event,*args):
        if event=="InsertLeave":
            self._nvim.call('airline#extensions#cm_call_signature#set', '', async=True)

    def cm_refresh(self,info,ctx,*args):

        lnum = ctx['lnum']
        col = ctx['col']
        typed = ctx['typed']

        kwtyped = re.search(r'[0-9a-zA-Z_]*?$',typed).group(0)
        startcol = col-len(kwtyped)

        path, filetype = self._nvim.eval('[expand("%:p"),&filetype]')
        if filetype not in ['python','markdown']:
            logger.info('ignore filetype: %s', filetype)
            return

        src = "\n".join(self._nvim.current.buffer[:])

        if filetype=='markdown':
            result = cm_utils.check_markdown_code_block(src,['python'],lnum, col)
            logger.info('try markdown, %s,%s,%s, result: %s', src, col, col, result)
            if result is None:
                return
            src = result['src']
            col = result['col']
            lnum = result['lnum']

        script = jedi.Script(src, lnum, len(typed), path)
        completions = script.completions()
        logger.info('completions %s', completions)
        
        signature_text = self._get_signature_text(script)

        self._nvim.call('airline#extensions#cm_call_signature#set', signature_text, async=True)

        # skip completions
        skip = False

        # completion pattern
        if (re.search(r'^(import|from)', typed) 
            or re.search(r'[\w_]{2,}$',typed)
            or re.search(r'\.[\w_]*$',typed)
            ):
            skip = False
        else:
            skip = True

        if skip:
            # if skip the completions, show the useful call_signatures
            if kwtyped=="" and signature_text:
                matches = [dict(word='',empty=1,abbr=signature_text,dup=1),]
                self._nvim.call('cm#complete', info['name'], ctx, col, matches, async=True)
            return

        matches = []

        for complete in completions:
            
            item = dict(word=kwtyped+complete.complete,
                        icase=1,
                        dup=1,
                        menu=complete.description,
                        info=complete.docstring()
                        )
            # Fix the user typed case
            if item['word'].lower()==complete.name.lower():
                item['word'] = complete.name
            matches.append(item)

        # cm#complete(src, context, startcol, matches)
        ret = self._nvim.call('cm#complete', info['name'], ctx, startcol, matches)
        logger.info('matches %s, ret %s', matches, ret)

    def _get_signature_text(self,script):
        signature_text = ''
        # TODO: optimize
        # currently simply use the last signature
        signatures = script.call_signatures()
        logger.info('signatures: %s', signatures)
        if len(signatures)>0:
            signature = signatures[-1]
            params=[param.description for param in signature.params]
            signature_text = signature.name + '(' + ', '.join(params) + ')'
        return signature_text

