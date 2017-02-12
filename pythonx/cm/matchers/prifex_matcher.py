# -*- coding: utf-8 -*-


class Matcher(object):

    def __init__(self,nvim):
        ignorecase,sartcase = nvim.eval('[&ignorecase,&smartcase]')
        if ignorecase:
            if smartcase:
                self._match = self._match_smart_case
            else:
                self._match = self._match_icase
        else:
            self._match = self._match_case

    def process(self,name,ctx,startcol,matches):

        base = ctx['typed'][startcol-1:]

        matches = [m for m in matches if self._match(base,m)]

        # in python, 'A' sort's before 'a', we need to swapcase for the 'a'
        # sorting before 'A'
        matches.sort(key=lambda e: e['word'].swapcase())

        return matches

    def _match_smart_case(self,base,item):
        if len(base)>len(item['word']):
            return False
        for a,b in zip(base,item['word']):
            if a.isupper() :
                if a!=b:
                    return False
            elif a!=b.lower():
                return False
        return True

    def _match_case(self,base,item):
        return base == item['word'][0:len(base)]

    def _match_icase(self,base,item):
        return base.lower() == item['word'][0:len(base)].lower()

