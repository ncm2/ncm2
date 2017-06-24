# -*- coding: utf-8 -*-

# For debugging, use this command to start neovim:
#
# NVIM_PYTHON_LOG_FILE=nvim.log NVIM_PYTHON_LOG_LEVEL=INFO nvim
#
#
# Please register source before executing any other code, this allow cm_core to
# read basic information about the source without loading the whole module, and
# modules required by this module
from cm import register_source, getLogger, Base

# A completion source with CTRL-X CTRL-N like feature
#
# sort=0 for not using NCM's builtin sorting
# auto_popup=0, this source is kinkd of heavy weight (scan all buffers)
register_source(name='cm-keyword-continue',
                priority=5,
                abbreviation='',
                word_pattern=r'\w+',
                cm_refresh_length=0,
                auto_popup=0,
                sort=0,)

import re
import copy

logger = getLogger(__name__)

class Source(Base):

    def __init__(self,nvim):
        super().__init__(nvim)

    def cm_refresh(self,info,ctx,*args):

        force = ctx.get('force',False)

        compiled = re.compile(info['word_pattern'])

        typed = ctx['typed']
        if typed.strip()=='' and not force:
            # At the beginning of the line, need force to trigger the popup,
            # Otherwise this will be annoying.
            return
        try:
            # fetch the previous line for better sorting
            last_line = self.nvim.current.buffer[ctx['lnum']-2]
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

        def compact_hint(rest_of_line,maxlen):
            words = list(compiled.finditer(rest_of_line))
            # to the last non word sequence
            words_in_range = [e for e in words if e.span()[0]<=maxlen]
            if not words_in_range:
                return ''
            end = words_in_range[-1].span()[0]
            return rest_of_line[0:end]

        lnum = ctx['lnum']
        bufnr = self.nvim.current.buffer.number

        for buffer in self.nvim.buffers:

            this_bufnr = buffer.number
            def word_generator():
                step = 500
                line_cnt = len(buffer)
                this_lnum = 1
                for i in range(0,min(line_cnt,5000),step):
                    lines = buffer[i:i+step]
                    last_line = ''
                    for line in lines:
                        try:
                            if this_lnum==lnum and bufnr==this_bufnr:
                                # pass current editting line
                                continue
                            for word in re.finditer(compiled,line):
                                yield word.group(),word.span(),line,last_line
                        finally:
                            last_line = line
                            this_lnum += 1

            try:
                tmp_prev_word = ''
                tmp_prev_span = (0,0)
                for word,span,line,last_line in word_generator():
                    if tmp_prev_word==prev_word:

                        rest_of_line = line[span[0]:]

                        if len(rest_of_line)<50:
                            hint = rest_of_line
                        else:
                            hint = compact_hint(rest_of_line,50)

                        rest_of_line_without_this = line[span[1]:]
                        next_word = compiled.search(rest_of_line_without_this)
                        if not next_word:
                            next_non_word = rest_of_line_without_this
                        else:
                            next_non_word = rest_of_line_without_this[0: next_word.span()[0]]
                        # word = word + next_non_word_sequence
                        matches.append(dict(word=word + next_non_word, menu=hint, _rest_of_line=rest_of_line, _rank=get_rank(word,span,line,last_line)))
                    tmp_prev_word = word
                    tmp_prev_span = span
            except Exception as ex:
                logger.exception("Parsing buffer [%s] failed", buffer)

        # sort the result based on total match
        matches.sort(key=lambda e: e['_rank'], reverse=True)

        if not force:
            # filter by ranking
            matches = [e for e in matches if e['_rank']>=3 ]

        # filter the result here, so that the result of line completion will be
        # displayed properly
        matches = self.matcher.process(info, ctx, ctx['startcol'], matches)

        if matches:
            # add rest_of_line completion for the highest rank
            e = copy.deepcopy(matches[0])
            # e['abbr'] = e['word'] + e['menu'] + '...'
            e['abbr'] = 'the rest> '
            hint = e['menu']
            if len(hint) < len(e['_rest_of_line']):
                hint += ' ...'
            e['menu'] = e['word'] + hint
            e['word'] = e['_rest_of_line']
            matches.insert(1,e)

        # if not matches:
        #     return

        logger.info('matches %s', matches)
        self.complete(info, ctx, ctx['startcol'], matches)

