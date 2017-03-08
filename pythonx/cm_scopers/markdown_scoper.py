# -*- coding: utf-8 -*-
import re
import logging
import copy
from cm import Base, getLogger

logger = getLogger(__name__)

class Scoper(Base):

    scopes = ['markdown']

    def sub_context(self,ctx,src):

        import mistune

        # hack preprocessing, this affects character counting
        def preprocessing(text, tab=4):
            # text = _newline_pattern.sub('\n', text)
            # text = text.replace('\t', ' ' * tab)
            # text = text.replace('\u00a0', ' ')
            # text = text.replace('\u2424', '\n')
            # pattern = re.compile(r'^ +$', re.M)
            # return pattern.sub('', text)
            return text

        mistune.preprocessing = preprocessing

        # hack fences, to make m.end(3) the end of code block
        # fences = re.compile(
        #     r'^ *(`{3,}|~{3,}) *(\S+)? *\n'  # ```lang
        #     r'([\s\S]+?)\s*'
        #     r'\1 *(?:\n+|$)'  # ```
        # )
        mistune.BlockGrammar.fences = re.compile(
            r'^ *(`{3,}|~{3,}) *(\S+)? *\n'  # ```lang
            r'([\s\S]+?\s*)'
            r'\1 *(?:\n+|$)'  # ```
        )

        # hack the lexer to find this markdown code block on the current cursor
        class HackBlockLexer(mistune.BlockLexer):
            def parse(self, text, rules=None):
                text = text.rstrip('\n')
                if not rules:
                    rules = self.default_rules
                def manipulate(text,pos):
                    for key in rules:
                        rule = getattr(self.rules, key)
                        m = rule.match(text)
                        if not m:
                            continue
                        if (key=='fences' 
                            and m.group(2)  # language
                            and pos+m.start(3) <= self.cm_cur_pos 
                            and pos+m.end(3) > self.cm_cur_pos
                            ):
                            self.cm_scope_info = dict(src = text[m.start(3):m.end(3)],
                                                      pos = self.cm_cur_pos-(pos+m.start(3)),
                                                      scope_offset = pos+m.start(3),
                                                      scope = m.group(2),
                                                           )
                            logger.info('group: %s', m.group(0))
                        getattr(self, 'parse_%s' % key)(m)
                        return m
                    return False  # pragma: no cover
                pos = 0
                while text:
                    m = manipulate(text,pos)
                    if m is not False:
                        pos+=len(m.group(0))
                        text = text[len(m.group(0)):]
                        continue
                    if text:  # pragma: no cover
                        raise RuntimeError('Infinite loop at: %s' % text)
                return self.tokens

        block = HackBlockLexer()
        block.cm_scope_info = None

        pos = self.get_pos(ctx['lnum'],ctx['col'],src)

        block.cm_cur_pos = pos
        mistune.markdown(src,block=block)

        if not block.cm_scope_info:
            return None

        new_pos = block.cm_scope_info['pos']
        new_src = block.cm_scope_info['src']
        p = 0
        for idx,line in enumerate(new_src.split("\n")):
            if (p<=new_pos) and (p+len(line)+1>new_pos):
                new_ctx = copy.deepcopy(ctx)
                new_ctx['scope'] = block.cm_scope_info['scope']
                new_ctx['lnum'] = idx+1
                new_ctx['col'] = new_pos-p+1
                new_ctx['scope_offset'] = block.cm_scope_info['scope_offset']
                new_ctx['scope_len'] = len(new_src)
                lnum_col = self.get_lnum_col(block.cm_scope_info['scope_offset'],src)
                new_ctx['scope_lnum'] = lnum_col[0]
                new_ctx['scope_col'] = lnum_col[1]
                return new_ctx
            else:
                p += len(line)+1

        return None

