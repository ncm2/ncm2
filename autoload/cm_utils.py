

import re
import logging

logger = logging.getLogger(__name__)

def check_markdown_code_block(doc,languages,lnum,col):

    try:
        import mistune

        # hack the lexer to find this markdown code block
        class HackBLockLexer(mistune.BlockLexer):
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
                            and (m.group(2) in languages)
                            and pos+m.start(3) <= self.cm_cur_pos 
                            and pos+len(m.group(0)) > self.cm_cur_pos
                            ):
                            self.cm_current_py_info = dict(src=text[m.start(3):],
                                                           pos=self.cm_cur_pos-(pos+m.start(3)))
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

        block = HackBLockLexer()
        block.cm_current_py_info = None

        # curpos
        lines = doc.split('\n')
        pos = 0
        for i in range(lnum-1):
            pos += len(lines[i])+1
        pos += col-1

        block.cm_cur_pos = pos
        mistune.markdown(doc,block=block)

        if block.cm_current_py_info:
            pos = block.cm_current_py_info['pos']
            src = block.cm_current_py_info['src']
            p = 0
            for idx,line in enumerate(src.split("\n")):
                if p<=pos and (p+len(line))>=pos:
                    block.cm_current_py_info['lnum'] = idx+1
                    block.cm_current_py_info['col'] = pos-p+1
                    block.cm_current_py_info['pos'] = pos
                    return block.cm_current_py_info
                p += len(line)+1

        return None

    except Exception as ex:
        logger.info('exception, %s', ex)
        return None


