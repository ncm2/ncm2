# -*- coding: utf-8 -*-


class Matcher(object):

    def __init__(self,nvim,extra=None):
        if extra not in ['case','icase','smartcase']:
            ignorecase,sartcase = nvim.eval('[&ignorecase,&smartcase]')
            if smartcase:
                self._chcmp = self._chcmp_smartcase
            elif ignorecase:
                self._chcmp = self._chcmp_icase
            else:
                self._chcmp = self._chcmp_case
        elif extra=='case':
            self._chcmp = self._chcmp_case
        elif extra=='icase':
            self._chcmp = self._chcmp_icase
        elif extra=='smartcase':
            self._chcmp = self._chcmp_smartcase

    def process(self,name,ctx,startcol,matches):

        base = ctx['typed'][startcol-1:]

        tmp = []
        for item in matches:
            score = self._match(base,item)
            if not score:
                continue
            tmp.append((item,score))

        # sort by score, the smaller the better
        tmp.sort(key=lambda e: e[1])

        return [e[0] for e in tmp]

    # return the score, the smaller the better
    def _match(self, base, item):

        word = item['word']
        if len(base)>len(word):
            return None
        p = -1
        pend = len(word)
        begin = pend
        for c in base:
            p += 1
            if p>=pend:
                return None
            while not self._chcmp(c,word[p]):
                p += 1
                if p>=pend:
                    return None
            if p < begin:
                begin = p

        # return the score, the smaller the better
        return (p-begin, len(word), word.swapcase())

    def _chcmp_smartcase(self,a,b):
        if a.isupper():
            return a==b
        else:
            return a == b.lower()

    def _chcmp_case(self,a,b):
        return a==b

    def _chcmp_icase(self,a,b):
        return a.lower()==b.lower()

