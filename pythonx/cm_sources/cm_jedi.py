# -*- coding: utf-8 -*-

# For debugging
# NVIM_PYTHON_LOG_FILE=nvim.log NVIM_PYTHON_LOG_LEVEL=INFO nvim

# detach 1 for quick shutdown for neovim, detach 0, 'cause jedi enters infinite
# loops sometime, don't know why.
from cm import get_src, register_source
register_source(name='cm-jedi',
                priority=9,
                abbreviation='Py',
                scoping=True,
                scopes=['python'],
                # The last two patterns is for displaying function signatures [r'\(\s?',r',\s?']
                cm_refresh_patterns=[r'^(import|from).*?\s(\w*)$', r'(\w{3,})$',r'\.(\w*)$',r'\(\s?',r',\s?'],
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

        path = ctx['filepath']

        src = get_src(self._nvim,ctx)
        if not src.strip():
            # empty src may possibly block jedi execution, don't know why
            logger.info('ignore empty src [%s]', src)
            return

        # logger.info('jedi.Script lnum[%s] curcol[%s] path[%s] [%s]', lnum,len(typed),path,src)
        script = jedi.Script(src, ctx['lnum'], len(ctx['typed']), path)

        # if the framework doesn't pass the startcol, it means the pattern for
        # displaying call signature has matched
        if not ctx.get('startcol',None):
            # try show the call signature
            signature_text = self._get_signature_text(script)
            if signature_text:
                matches = [dict(word='',empty=1,abbr=signature_text,dup=1),]
                # refresh=True
                # call signature popup doesn't need to be cached by the framework
                self._nvim.call('cm#complete', info['name'], ctx, ctx['col'], matches, True, async=True)
            return

        completions = script.completions()
        logger.info('completions %s', completions)

        matches = []

        for complete in completions:
            
            item = dict(word=ctx['base']+complete.complete,
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
        ret = self._nvim.call('cm#complete', info['name'], ctx, ctx['startcol'], matches, async=True)
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

