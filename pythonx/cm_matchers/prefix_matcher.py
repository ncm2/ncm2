# -*- coding: utf-8 -*-


class Matcher(object):

    def __init__(self,nvim,chcmp,*args):
        self._chcmp = chcmp

    def process(self,name,ctx,startcol,matches):

        base = ctx['typed'][startcol-1:]

        matches = [m for m in matches if self._match(base,m)]

        # in python, 'A' sort's before 'a', we need to swapcase for the 'a'
        # sorting before 'A'
        matches.sort(key=lambda e: e['word'].swapcase())

        return matches

    def _match(self,base,item):
        if len(base)>len(item['word']):
            return False
        for a,b in zip(base,item['word']):
            if not self._chcmp(a,b):
                return False
        return True

