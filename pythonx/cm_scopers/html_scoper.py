# -*- coding: utf-8 -*-
import re
import logging
import copy
from cm import Base, getLogger

logger = getLogger(__name__)

class Scoper(Base):

    scopes = ['html','xhtml','php','blade','jinja','jinja2','vue.html.javascript.css','vue']

    def sub_context(self,ctx,src):

        lnum = ctx['lnum']
        col = ctx['col']
        from html.parser import HTMLParser

        scoper = self

        class MyHTMLParser(HTMLParser):

            last_data_start = None
            last_data = None

            scope_info = None
            skip = False

            def handle_starttag(self,tag,attrs):

                self.skip = False

                if tag in ['style','script']:
                    for attr in attrs:
                        try:
                            # avoid css completion for lang="stylus"
                            if tag=='style' and attr[0]=='lang' and attr[1] and attr[1] not in ['css','scss']:
                                self.skip = True
                                return
                            if tag=='style' and attr[0]=='type' and attr[1] and attr[1] not in ['text/css']:
                                self.skip = True
                                return
                            if tag=='script' and attr[0]=='type' and attr[1] and attr[1] not in ['text/javascript']:
                                self.skip = True
                                return
                        except:
                            pass

            def handle_endtag(self, tag):

                if self.skip:
                    return

                if tag in ['style','script']:

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

                        if tag=='script':
                            self.scope_info['scope']='javascript'
                        else:
                            # style
                            self.scope_info['scope']='css'

                        self.scope_info['scope_offset']= scoper.get_pos(startpos[0],startpos[1]+1,src)
                        self.scope_info['scope_len']=len(self.last_data)

                        # offset as lnum, col format
                        self.scope_info['scope_lnum']= startpos[0]
                        # startpos[1] is zero based
                        self.scope_info['scope_col']= startpos[1]+1


            def handle_data(self, data):
                self.last_data = data
                self.last_data_start = self.getpos()

        parser = MyHTMLParser()
        parser.feed(src)
        if parser.scope_info:

            new_ctx = copy.deepcopy(ctx)
            new_ctx['scope'] = parser.scope_info['scope']
            new_ctx['lnum'] = parser.scope_info['lnum']
            new_ctx['col'] = parser.scope_info['col']

            new_ctx['scope_offset'] = parser.scope_info['scope_offset']
            new_ctx['scope_len'] = parser.scope_info['scope_len']
            new_ctx['scope_lnum'] = parser.scope_info['scope_lnum']
            new_ctx['scope_col'] = parser.scope_info['scope_col']

            return new_ctx


        pos = self.get_pos(lnum,col,src)
        # css completions for style='|'
        for match in re.finditer(r'style\s*=\s*("|\')(.*?)\1',src):
            if match.start(2)>pos:
                return
            if match.end(2)<pos:
                continue
            # start < pos and and>=pos
            new_src = match.group(2)

            new_ctx = copy.deepcopy(ctx)
            new_ctx['scope'] = 'css'

            new_ctx['scope_offset'] = match.start(2)
            new_ctx['scope_len'] = len(new_src)
            scope_lnum_col = self.get_lnum_col(match.start(2),src)
            new_ctx['scope_lnum'] = scope_lnum_col[0]
            new_ctx['scope_col'] = scope_lnum_col[1]

            sub_pos = pos - match.start(2)
            sub_lnum_col = self.get_lnum_col(sub_pos,new_src)
            new_ctx['lnum'] = sub_lnum_col[0]
            new_ctx['col'] = sub_lnum_col[1]
            return new_ctx
        
        return None


