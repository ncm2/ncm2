# -*- coding: utf-8 -*-

# For debugging, use this command to start neovim:
#
# NVIM_PYTHON_LOG_FILE=nvim.log NVIM_PYTHON_LOG_LEVEL=INFO nvim
#
#
# Please register source before executing any other code, this allow cm_core to
# read basic information about the source without loading the whole module, and
# modules required by this module
from cm import get_src, register_source, get_pos, getLogger

# A completion source with CTRL-X CTRL-N like feature
#
# sort=0 for not using NCM's builtin sorting
register_source(name='cm-keyword-continue',
                priority=6,
                abbreviation='',
                word_pattern=r'\S+',
                sort=0,
                cm_refresh_patterns=[r'\s+$'],)

import re

logger = getLogger(__name__)


class Source:

    def __init__(self,nvim):

        self._nvim = nvim

    def cm_refresh(self,info,ctx,*args):

        force = ctx.get('force',False)

        compiled = re.compile(info['word_pattern'])

        typed = ctx['typed']
        try:
            # fetch the previous line for better sorting
            last_line = self._nvim.current.buffer[ctx['lnum']-2]
            typed = last_line + '\n' + typed
        except:
            pass

        typed_words = re.findall(compiled,typed)

        if not typed_words:
            return

        prev_word = ''
        if ctx['base']=='':
            prev_word = typed_words[-1]
            prev_words = typed_words
        else:
            if len(typed_words)<2:
                return
            prev_word = typed_words[-2]
            prev_words = typed_words[0:-1]

        if not isinstance(prev_word,str):
            prev_word = prev_word[0]
            prev_words = [e[0] for e in prev_words]

        reversed_prev_words = list(reversed(prev_words))
        matches = []

        # rank for sorting
        def get_rank(word,span,line,last_line):
            prev = last_line+"\n"+line[0:span[0]]
            words = re.findall(compiled,prev)
            if not words:
                return 0
            if not isinstance(words[0],str):
                words = [e[0] for e in words]
            ret = 0
            reserved_words = list(reversed(words))
            for z in zip(reversed_prev_words,reserved_words):
                if z[0].lower()==z[1].lower():
                    ret += 1
                else:
                    break
            return ret

        for buffer in self._nvim.buffers:

            def word_generator():
                step = 200
                line_cnt = len(buffer)
                for i in range(0,line_cnt,step):
                    lines = buffer[i:i+step]
                    last_line = ''
                    for line in lines:
                        for word in re.finditer(compiled,line):
                            yield word.group(),word.span(),line,last_line
                        last_line = line

            try:
                tmp_prev_word = ''
                for word,span,line,last_line in word_generator():
                    if tmp_prev_word==prev_word:
                        matches.append(dict(word=word + re.findall(r'\s*',line[span[1]:])[0], info=line[span[1]:], _rank=get_rank(word,span,line,last_line)))
                    tmp_prev_word = word
            except Exception as ex:
                logger.exception("Parsing buffer [%s] failed", buffer)

        # sort the result based on total match
        matches.sort(key=lambda e: e['_rank'], reverse=True)

        if not force:
            # filter by ranking
            matches = [e for e in matches if e['_rank']>=3 ]

        logger.info('matches %s', matches)
        ret = self._nvim.call('cm#complete', info['name'], ctx, ctx['startcol'], matches)

