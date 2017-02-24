# -*- coding: utf-8 -*-

# For debugging
# NVIM_PYTHON_LOG_FILE=nvim.log NVIM_PYTHON_LOG_LEVEL=INFO nvim

# detach 1 for quick shutdown for neovim, detach 0, 'cause jedi enters infinite
# loops sometime, don't know why.
import cm
cm.register_source(name='cm-jedi',
                   priority=9,
                   abbreviation='Py',
                   scoping=True,
                   scopes=['python'],
                   events=['InsertLeave'],
                   detach=0)

import os
import re
import logging
import jedi
from neovim import attach, setup_logging

logger = logging.getLogger(__name__)

class Source:

    def __init__(self,nvim):

        self._nvim = nvim

    def cm_refresh(self,info,ctx,*args):

        lnum = ctx['lnum']
        col = ctx['col']
        typed = ctx['typed']
        path = ctx['filepath']

        kwtyped = re.search(r'[0-9a-zA-Z_]*?$',typed).group(0)
        startcol = col-len(kwtyped)


        src = cm.get_src(ctx)
        if not src.strip():
            # empty src may possibly block jedi execution, don't know why
            logger.info('ignore empty src [%s]', src)
            return

        skip_completions = False
        show_sig = False

        # completion pattern
        if (re.search(r'^(import|from)', typed) 
            or re.search(r'[\w_]{2,}$',typed)
            or re.search(r'\.[\w_]*$',typed)
            ):
            skip_completions = False
        else:
            skip_completions = True
            if kwtyped=="":
                show_sig = True
            else:
                # skip and no show sig, no need to process
                return

        # logger.info('jedi.Script lnum[%s] curcol[%s] path[%s] [%s]', lnum,len(typed),path,src)
        script = jedi.Script(src, lnum, len(typed), path)

        if show_sig:
            signature_text = self._get_signature_text(script)
            if signature_text:
                matches = [dict(word='',empty=1,abbr=signature_text,dup=1),]
                self._nvim.call('cm#complete', info['name'], ctx, col, matches, True, async=True)
            return

        if skip_completions:
            return

        completions = script.completions()
        logger.info('completions %s', completions)

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
        ret = self._nvim.call('cm#complete', info['name'], ctx, startcol, matches, async=True)
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

