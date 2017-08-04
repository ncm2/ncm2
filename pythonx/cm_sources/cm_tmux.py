#!/usr/bin/env python
# -*- coding: utf-8 -*-

# For debugging
# NVIM_PYTHON_LOG_FILE=nvim.log NVIM_PYTHON_LOG_LEVEL=INFO nvim

from cm import register_source, getLogger, Base
import os
register_source(name='cm-tmux',
                abbreviation='Tmux',
                priority=4,
                enable= 'TMUX' in os.environ,
                events=['CursorHold','CursorHoldI','FocusGained','BufEnter'],)

import os
import re
import logging
import subprocess

logger = getLogger(__name__)

class Source(Base):

    def __init__(self,nvim):
        super().__init__(nvim)

        self._words = set()

        self._split_pattern = r'[^\w]+'
        self._kw_pattern = r'\w'

        self.refresh_keyword()

    def cm_event(self,event,ctx,*args):
        if event in ['CursorHold','CursorHoldI','FocusGained','BufEnter']:
            logger.info('refresh_keyword on event %s', event)
            self.refresh_keyword()


    def refresh_keyword(self):
        pat = re.compile(self._split_pattern)
        self._words = set()

        # tmux list-window -F '#{window_index}'
        # tmux capture-pane -p -t "$window_index.$pane_index"
        proc = subprocess.Popen(args=['tmux', 'list-window', '-F', '#{window_index}'],
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)

        outs, errs = proc.communicate(timeout=15)
        window_indices = outs.decode('utf-8')
        logger.info('list-window: %s', window_indices)

        # parse windows
        panes = []
        for win_index in window_indices.strip().split('\n'):
            proc = subprocess.Popen(args=['tmux', 'list-panes', '-t', win_index, '-F', '#{pane_index}'],
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            outs, errs = proc.communicate(timeout=15)
            pane_ids = outs.decode('utf-8')

            for pane_id in pane_ids.strip().split('\n'):
                proc = subprocess.Popen(args=['tmux', 'capture-pane', '-p', '-t', '{}.{}'.format(win_index,pane_id)],
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
                outs, errs = proc.communicate(timeout=15)
                try:
                    outs = outs.decode('utf-8')
                    panes.append(outs)
                except Exception as ex:
                    logger.exception('exception, failed to decode output, %s', ex)
                    pass

        for pane in panes:
            for word in re.split(pat,pane):
                self._words.add(word)

        logger.info('keyword refresh complete, count: %s', len(self._words))


    def cm_refresh(self,info,ctx):

        startcol = ctx['startcol']

        matches = (dict(word=word,icase=1)  for word in self._words)
        matches = self.matcher.process(info, ctx, startcol, matches)

        self.complete(info, ctx, ctx['startcol'], matches)

