# -*- coding: utf-8 -*-


class Matcher(object):

    def __init__(self,nvim,chcmp,*args):
        self._chcmp = chcmp

    def process(self,info,ctx,startcol,matches):

        # fix for chinese characters
        # `你好 abcd|` 
        # has  col('.')==11 on vim
        # the evaluated startcol is: startcol[8] typed[你好 abcd]
        # but in python, "你好 abcd"[8] is not a valid index
        begin = -(ctx['col'] - startcol)
        base = ''
        if begin:
            base = ctx['typed'][begin:]

        ret = [m for m in matches if self._match(base,m)]

        if info['sort']:
            # in python, 'A' sort's before 'a', we need to swapcase for the 'a'
            # sorting before 'A'
            ret.sort(key=lambda e: e['word'].swapcase())

        return ret

    def _match(self,base,item):
        if len(base)>len(item['word']):
            return False
        for a,b in zip(base,item['word']):
            if not self._chcmp(a,b):
                return False
        return True

