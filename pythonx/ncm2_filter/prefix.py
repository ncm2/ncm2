# -*- coding: utf-8 -*-


class Filter:

    def smart_case_match(self, b: str, w: str):
        if len(b) != len(w):
            return False
        for c1, c2 in zip(b, w):
            if c1 == c2:
                continue
            if c1.lower() != c2.lower():
                return False
            if c1.islower():
                continue
            else:
                return False
        return True

    def __init__(self, c='smartcase'):
        if c == 'smartcase':
            self._match = lambda b, w: self.smart_case_match(b, w)
        elif c == 'icase':
            self._match = lambda b, w: b.lower() == w.lower()
        else:
            self._match = lambda b, w: b == w

    def filter(self, base, matches):
        ret = []
        ln = len(base)
        for m in matches:
            w = m['word']
            if self._match(base, w[:ln]):
                m['user_data']['word_highlight'] = [[0, ln]]
                ret.append(m)
        return ret
