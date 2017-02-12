# -*- coding: utf-8 -*-
import re
import logging
import urllib
import http.client
import copy
from cm import cm

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Scoper:

    scopes = ['html','xhtml','php','blade','jinja','jinja2']

    def sub_context(self,ctx,src):

        lnum = ctx['lnum']
        col = ctx['col']
        from html.parser import HTMLParser

        class MyHTMLParser(HTMLParser):

            last_data_start = None
            last_data = None

            scope_info = None

            def handle_endtag(self, tag):

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

                        self.scope_info['scope_offset']= cm.get_pos(dict(lnum=startpos[0],col=startpos[1]+1),src)
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
        if not parser.scope_info:
            return None

        new_ctx = copy.deepcopy(ctx)
        new_ctx['scope'] = parser.scope_info['scope']
        new_ctx['lnum'] = parser.scope_info['lnum']
        new_ctx['col'] = parser.scope_info['col']

        new_ctx['scope_offset'] = parser.scope_info['scope_offset']
        new_ctx['scope_len'] = parser.scope_info['scope_len']
        new_ctx['scope_lnum'] = parser.scope_info['scope_lnum']
        new_ctx['scope_col'] = parser.scope_info['scope_col']

        return new_ctx

