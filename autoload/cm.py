

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

# convert (lnum, col) to pos
def get_pos(ctx,src):

    lnum = ctx['lnum']
    col = ctx['col']

    # curpos
    lines = src.split('\n')
    pos = 0
    for i in range(lnum-1):
        pos += len(lines[i])+1
    pos += col-1

    return pos




class MarkdownScope:

    def get_subscope_ctx(self,ctx,src):

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

            pos = get_pos(ctx,src)

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
                    return new_ctx
                else:
                    p += len(line)+1

            return None


        except Exception as ex:
            logger.info('exception, %s', ex)
            return None

class HtmlScope:

    def get_subscope_ctx(self,ctx,src):

        lnum = ctx['lnum']
        col = ctx['col']
        from html.parser import HTMLParser

        class MyHTMLParser(HTMLParser):

            last_data_start = None
            last_data = None

            scope_info = None

            def handle_endtag(self, tag):

                if tag=='script':
                    startpos = self.last_data_start
                    endpos = self.getpos()
                    if ((startpos[0]<lnum 
                        or (startpos[0]==lnum
                            and startpos[1]+1<=col))
                        and
                        (endpos[0]>lnum
                         or (endpos[0]==lnum
                             and endpos[1]>=col))
                        ):

                        self.scope_info = {}
                        self.scope_info['lnum'] = lnum-startpos[0]+1
                        if lnum==startpos[0]:
                            self.scope_info['col'] = col-(startpos[1]+1)+1
                        else:
                            self.scope_info['col']=col
                        self.scope_info['scope']='javascript'
                        self.scope_info['scope_offset']=get_pos(dict(lnum=startpos[0],col=startpos[1]+1),src)
                        self.scope_info['scope_len']=len(self.last_data)

                elif tag=='style':
                    startpos = self.last_data_start
                    endpos = self.getpos()
                    if ((startpos[0]<lnum 
                        or (startpos[0]==lnum
                            and startpos[1]+1<=col))
                        and
                        (endpos[0]>lnum
                         or (endpos[0]==lnum
                             and endpos[1]>=col))
                        ):

                        self.scope_info = {}
                        self.scope_info['lnum'] = lnum-startpos[0]+1
                        if lnum==startpos[0]:
                            self.scope_info['col'] = col-(startpos[1]+1)+1
                        else:
                            self.scope_info['col']=col
                        self.scope_info['scope']='css'
                        self.scope_info['scope_offset']=get_pos(dict(lnum=startpos[0],col=startpos[1]+1),src)
                        self.scope_info['scope_len']=len(self.last_data)

            def handle_data(self, data):
                self.last_data = data
                self.last_data_start = self.getpos()

        parser = MyHTMLParser()
        parser.feed(src)
        if not parser.scope_info:
            return None

        new_ctx = copy.deepcopy(ctx)
        new_ctx['scope'] = parser.scope_info['scope']
        new_ctx['lnum'] = parser.scope_info['lnum']
        new_ctx['col'] = parser.scope_info['col']
        new_ctx['scope_offset'] = parser.scope_info['scope_offset']
        new_ctx['scope_len'] = parser.scope_info['scope_len']
        return new_ctx


