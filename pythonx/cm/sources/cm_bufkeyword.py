#!/usr/bin/env python
# -*- coding: utf-8 -*-

# For debugging
# NVIM_PYTHON_LOG_FILE=nvim.log NVIM_PYTHON_LOG_LEVEL=INFO nvim

from cm import cm
cm.register_source(name='cm-bufkeyword',
                   priority=5,
                   abbreviation='Key',
                   events=['CursorHold','CursorHoldI','BufEnter','BufWritePost','TextChangedI'],
                   cm_refresh_patterns=[r'[0-9a-zA-Z_#]{3,}$'],
                   detach=1)

import os
import re
import logging

logger = logging.getLogger(__name__)

class Source:

    def __init__(self,nvim):

        self._nvim = nvim
        self._words = set()

        self._split_pattern = r'[^0-9a-zA-Z_#]+'
        self._kw_pattern = r'[0-9a-zA-Z_#]'

        self._last_ctx = None

        self.refresh_keyword()

    def cm_event(self,event,ctx,*args):
        if event=="TextChangedI":
            if ctx['typed'] and re.match(self._kw_pattern,ctx['typed'][-1]) is None:
                self.refresh_keyword_incr(ctx['typed'])
        elif event in ['CursorHold','CursorHoldI','BufEnter','BufWritePost']:
            if self._last_ctx == ctx:
                return
            self._last_ctx = ctx
            self.refresh_keyword()


    def refresh_keyword(self):
        logger.info('refresh_keyword')
        pat = re.compile(self._split_pattern)
        self._words = set()
        for line in self._nvim.current.buffer[:]:
            for word in re.split(pat,line):
                self._words.add(word)

        logger.info('keyword refresh complete, count: %s', len(self._words))

    def refresh_keyword_incr(self,line):

        logger.info('refresh_keyword_incr')
        pat = re.compile(self._split_pattern)

        for word in re.split(pat,line):
            self._words.add(word)

        logger.info('keyword refresh incr complete, count: %s', len(self._words))

    def cm_refresh(self,info,ctx):

        lnum = ctx['lnum']
        col = ctx['col']
        typed = ctx['typed']
        
        kw = re.search(self._kw_pattern+r'*?$',typed).group(0)
        startcol = col-len(kw)

        matches = (dict(word=word,icase=1)  for word in self._words)
        matches = cm.get_matcher(self._nvim).process(info['name'], ctx, startcol, matches)

        # cm#complete(src, context, startcol, matches)
        self._nvim.call('cm#complete', info['name'], ctx, startcol, matches, async=True)

