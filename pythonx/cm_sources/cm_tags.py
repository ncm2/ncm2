#!/usr/bin/env python
# -*- coding: utf-8 -*-

# For debugging
# NVIM_PYTHON_LOG_FILE=nvim.log NVIM_PYTHON_LOG_LEVEL=INFO nvim

from cm import register_source, getLogger, Base
register_source(name='cm-tags',
                   priority=6,
                   abbreviation='Tag',
                   events=['WinEnter'],)

import os
import re
import logging
import sys

logger = getLogger(__name__)

class Source(Base):

    def __init__(self,nvim):
        super().__init__(nvim)
        self._files = self.nvim.call('tagfiles')

    def cm_event(self,event,ctx,*args):
        if event=="WinEnter":
            self._files = self.nvim.call('tagfiles')

    def cm_refresh(self,info,ctx):

        tags = {}

        for file in self._files:
            try:
                for line in binary_search_lines_by_prefix(ctx['base'],file):
                    fields = line.split("\t")
                    if len(fields)<2:
                        continue
                    tags[fields[0]] = dict(word=fields[0],menu='Tag: '+fields[1])
            except Exception as ex:
                logger.exception('binary_search_lines_by_prefix exception: %s', ex)

        # unique
        matches = list(tags.values())

        # there are huge tag files sometimes, be careful here. it's meaningless
        # to have huge amout of results.
        refresh = False
        if len(matches)>100:
            matches = matches[0:100]
            refresh = True

        logger.info('matches len %s', len(matches))

        self.complete(info, ctx, ctx['startcol'], matches, refresh)


def binary_search_lines_by_prefix(prefix,filename):

    with open(filename,'r') as f:

        def yield_results():
            while True:
                line = f.readline()
                if not line:
                    return
                if line[:len(prefix)]==prefix:
                    yield line
                else:
                    return

        begin = 0
        f.seek(0,2)
        end  = f.tell()

        while begin<end:

            middle_cursor = int((begin+end)/2)

            f.seek(middle_cursor,0)
            f.readline()

            line1pos = f.tell()
            line1 = f.readline()

            line2pos = f.tell()
            line2 = f.readline()

            line2end = f.tell()

            key1 = '~~'
            # if f.readline() returns an empty string, the end of the file has
            # been reached
            if line1!='':
                key1 = line1[:len(prefix)]

            key2 = '~~'
            if line2!='':
                key2 = line2[:len(prefix)]

            if key1 >= prefix:
                if line2pos < end:
                    end = line2pos
                else:
                    # (begin) ... | line0 int((begin+end)/2) | line1 (end) | line2 |
                    #
                    # this assignment push the middle_cursor forward, it may
                    # also result in a case where begin==end
                    #
                    # do not use end = line1pos, may results in infinite loop
                    end = int((begin+end)/2)
                    if end==begin:
                        if key1 == prefix:
                            # find success
                            f.seek(line2pos,0)
                            yield from yield_results()
                        return
            elif key2 == prefix:
                # find success
                # key1 < prefix  && next line key2 == prefix
                f.seek(line2pos,0)
                yield from yield_results()
                return
            elif key2 < prefix:
                begin = line2end
                # if begin==end, then exit the loop
            else:
                # key1 < prefix &&  next line key2 > prefix here, not found
                return
