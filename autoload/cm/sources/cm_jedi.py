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

    def cm_refresh(self,info,ctx,*args):

        lnum = ctx['lnum']
        col = ctx['col']
        typed = ctx['typed']

        kwtyped = re.search(r'[0-9a-zA-Z_]*?$',typed).group(0)
        startcol = col-len(kwtyped)

        path, filetype = self._nvim.eval('[expand("%:p"),&filetype]')
        if filetype not in ['python','markdown']:
            logger.info('ignore filetype: %s', filetype)
            return

        src = "\n".join(self._nvim.current.buffer[:])

        if filetype=='markdown':
            result = get_markdown_python_block_info(src,lnum,col)
            logger.info('try markdown, %s,%s,%s, result: %s', src, col, col, result)
            if result is None:
                return
            src = result['src']
            col = result['col']
            lnum = result['lnum']

        script = jedi.Script(src, lnum, len(typed), path)
        completions = script.completions()
        logger.info('completions %s', completions)
        
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
            if kwtyped=="" and signature_text:
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
        ret = self._nvim.call('cm#complete', info['name'], ctx, startcol, matches)
        logger.info('matches %s, ret %s', matches, ret)

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

def get_markdown_python_block_info(doc,lnum,col):

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
                            and m.group(2)=='python'
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
                    return block.cm_current_py_info
                p += len(line)+1

        return None

    except Exception as ex:
        logger.info('exception, %s', ex)
        return None

