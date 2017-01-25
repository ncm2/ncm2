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

    def cm_refresh(self,info,ctx):

        lnum = ctx['curpos'][1]
        col = ctx['curpos'][2]
        line = self._nvim.current.buffer[lnum-1]
        typed = line[0 : col-1]

        # self.refresh_keyword_incr(line)

        kwtyped = re.search(r'[0-9a-zA-Z_]*?$',typed).group(0)
        startcol = col-len(kwtyped)

        if len(typed)==0:
            return
        elif len(kwtyped)>=2:
            pass
        elif len(kwtyped):
            return
        elif typed[-1]=='.':
            pass
        elif (typed[-1]==' ') and (typed[0:5]=='from ' or typed[0:7]=='import '):
            pass
        else:
            return

        matches = []

        path, filetype = self._nvim.eval('[expand("%:p"),&filetype]')
        if filetype!='python':
            logger.info('ignore filetype: %s', filetype)
            return

        src = "\n".join(self._nvim.current.buffer[:])
        scr = jedi.Script(src, lnum, len(typed), path)
        completions = scr.completions()

        for complete in completions:
            item = dict(word=kwtyped+complete.complete,icase=1,dup=1,abbr=complete.name)
            matches.append(item)

        # cm#complete(src, context, startcol, matches)
        self._nvim.call('cm#complete', info['name'], ctx, startcol, matches, async=True)

        logger.info('on changed, current line: %s, typed: [%s]', line, typed)

def main():

    # logging setup
    level = logging.INFO
    if 'NVIM_PYTHON_LOG_LEVEL' in os.environ:
        # TODO this affects the log file name
        setup_logging('cm_jedi')
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

