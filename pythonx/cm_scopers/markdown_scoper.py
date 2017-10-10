# -*- coding: utf-8 -*-
import re
import logging
import copy
from cm import Base, getLogger

logger = getLogger(__name__)

class Scoper(Base):

    scopes = ['markdown']

    def sub_context(self,ctx,src):

        scope = None
        pos = self.get_pos(ctx['lnum'], ctx['col'], src)

        pat = re.compile(
             r'^ (`{3,}|~{3,}) \s* (\S+)?  \s*  \n'
             r'(.+?)'
             r'^ \1 \s* (?:\n+|$)', re.M | re.X | re.S)

        for m in pat.finditer(src):
            if m.start() > pos:
                break
            if m.group(2) and m.start(3) <= pos and m.end(3) > pos:
                scope = dict(src=m.group(3),
                             pos=pos-m.start(3),
                             scope_offset=m.start(3),
                             scope=m.group(2))
                break

        if not scope:
            return None

        new_pos = scope['pos']
        new_src = scope['src']
        p = 0
        for idx,line in enumerate(new_src.split("\n")):
            if (p<=new_pos) and (p+len(line)+1>new_pos):
                new_ctx = copy.deepcopy(ctx)
                new_ctx['scope'] = scope['scope']
                new_ctx['lnum'] = idx+1
                new_ctx['col'] = new_pos-p+1
                new_ctx['scope_offset'] = scope['scope_offset']
                new_ctx['scope_len'] = len(new_src)
                lnum_col = self.get_lnum_col(scope['scope_offset'],src)
                new_ctx['scope_lnum'] = lnum_col[0]
                new_ctx['scope_col'] = lnum_col[1]
                return new_ctx
            else:
                p += len(line)+1

        return None

