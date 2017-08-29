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


        tmp = []
        for item in matches:
            score = self._match(base,item)
            if score is None:
                continue
            tmp.append((item,score))

        if info['sort']:
            # sort by score, the smaller the better
            tmp.sort(key=lambda e: e[1])

        return [e[0] for e in tmp]

    # return the score, the smaller the better
    def _match(self, base, item):

        word = item['word']
        if len(base)>len(word):
            return None

        if len(base) == 0:
            return 0

        for i in range(len(word)-len(base) + 1):
            match = True
            for j in range(len(base)):
                if not self._chcmp(base[j], word[i+j]):
                    match = False
                    break
            if match:
                return i

        return None

