#!/usr/bin/env python
# -*- coding: utf-8 -*-

# For debugging
# NVIM_PYTHON_LOG_FILE=nvim.log NVIM_PYTHON_LOG_LEVEL=INFO nvim

from cm import register_source, getLogger, Base
register_source(name='cm-bufkeyword',
                   priority=5,
                   abbreviation='Key',
                   events=['InsertEnter', 'BufEnter'],)

import re
import cm_default

logger = getLogger(__name__)

class Source(Base):

    def __init__(self,nvim):
        super(Source,self).__init__(nvim)
        self._words = set()
        self._last_ctx = None
        self.refresh_keyword(nvim.eval('cm#context()'))

    def cm_event(self,event,ctx,*args):
        if self._last_ctx and (self._last_ctx['changedtick'] == ctx['changedtick']):
            return
        self._last_ctx = ctx
        self.refresh_keyword(ctx)

    def refresh_keyword(self,ctx,all=True,expand=50):
        word_pattern = cm_default.word_pattern(ctx)
        compiled = re.compile(word_pattern)
        logger.info('refreshing_keyword, word_pattern [%s]', word_pattern)

        buffer = self.nvim.current.buffer

        if all:
            self._words = set()
            begin = 0
            end = len(buffer)
        else:
            begin = max(ctx['lnum']-50,0)
            end = min(ctx['lnum']+50,len(buffer))

        logger.info('keyword refresh begin, current count: %s', len(self._words))

        cur_lnum = ctx['lnum']
        cur_col = ctx['col']

        step = 1000
        for num in range(begin,end,step):
            lines = buffer[num:num+step]
            # convert 0 base to 1 base
            lnum = num+1
            for line in lines:
                if lnum == cur_lnum:
                    for word in compiled.finditer(line):
                        span = word.span()
                        # filter-out the word at current cursor
                        if (cur_col>=span[0]+1) and (cur_col-1<=span[1]+1):
                            continue
                        self._words.add(word.group())
                else:
                    for word in compiled.finditer(line):
                        self._words.add(word.group())
                lnum += 1

        logger.info('keyword refresh complete, count: %s', len(self._words))

    def cm_refresh(self,info,ctx):

        # incremental refresh
        self.refresh_keyword(ctx,False)

        matches = (dict(word=word,icase=1)  for word in self._words)
        matches = self.matcher.process(info, ctx, ctx['startcol'], matches)

        self.complete(info, ctx, ctx['startcol'], matches)

