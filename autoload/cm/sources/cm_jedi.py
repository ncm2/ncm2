# -*- coding: utf-8 -*-

# For debugging
# NVIM_PYTHON_LOG_FILE=nvim.log NVIM_PYTHON_LOG_LEVEL=INFO nvim

import os
import re
import logging
import jedi
from neovim import attach, setup_logging

logger = logging.getLogger(__name__)

class Handler:

    def __init__(self,nvim):

        self._nvim = nvim

    def cm_event(self,event,*args):
        if event=="InsertLeave":
            self._nvim.call('airline#extensions#cm_call_signature#set', '', async=True)

    def cm_refresh(self,info,ctx):

        lnum = ctx['lnum']
        col = ctx['col']
        typed = ctx['typed']

        kwtyped = re.search(r'[0-9a-zA-Z_]*?$',typed).group(0)
        startcol = col-len(kwtyped)

        path, filetype = self._nvim.eval('[expand("%:p"),&filetype]')
        if filetype!='python':
            logger.info('ignore filetype: %s', filetype)
            return

        src = "\n".join(self._nvim.current.buffer[:])
        script = jedi.Script(src, lnum, len(typed), path)
        completions = script.completions()
        
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
            if signature_text:
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
        self._nvim.call('cm#complete', info['name'], ctx, startcol, matches, async=True)

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

def main():

    # logging setup
    level = logging.INFO
    if 'NVIM_PYTHON_LOG_LEVEL' in os.environ:
        # TODO this affects the log file name
        setup_logging('cm-jedi')
        l = getattr(logging,
                os.environ['NVIM_PYTHON_LOG_LEVEL'].strip(),
                level)
        if isinstance(l, int):
            level = l
    logger.setLevel(level)

    # connect neovim
    nvim = attach('stdio')
    nvim_event_loop(nvim)

def nvim_event_loop(nvim):

    handler = Handler(nvim)

    def on_setup():
        logger.info('on_setup')

    def on_request(method, args):
        raise Exception('Not implemented')

    def on_notification(method, args):
        nonlocal handler
        logger.info('method: %s, args: %s', method, args)

        func = getattr(handler,method,None)
        if func is None:
            return

        func(*args)

    nvim.run_loop(on_request, on_notification, on_setup)

main()

