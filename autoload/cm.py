

import re
import logging
import urllib
import http.client
import copy

logger = logging.getLogger(__name__)

def get_src(ctx):
    src_uri = ctx['src_uri']
    parsed = urllib.parse.urlparse(src_uri)
    logger.info('hostname: %s, port %s, path: %s', parsed.hostname, parsed.port, parsed.path)
    conn = http.client.HTTPConnection(parsed.hostname, parsed.port)
    try:
        conn.request("GET", src_uri)
        res = conn.getresponse()
        src = res.read().decode('utf-8')
        res.close()
        return src
    finally:
        conn.close()
    return None


class MarkdownScope:

    def get_subscope_ctx(self,ctx,src):

        new_ctx = copy.deepcopy(ctx)

        lnum = ctx['lnum']
        col = ctx['col']

        try:

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

            # curpos
            lines = src.split('\n')
            pos = 0
            for i in range(lnum-1):
                pos += len(lines[i])+1
            pos += col-1

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
                    new_ctx['_new_pos'] = new_pos
                    new_ctx['_line_cnt'] = len(new_src.split("\n"))
                    new_ctx['_line'] = line
                    new_ctx['_len'] = len(line)
                    new_ctx['_p'] = p
                    new_ctx['_src'] = new_src
                    return new_ctx
                else:
                    p += len(line)+1

            return None


        except Exception as ex:
            logger.info('exception, %s', ex)
            return None


