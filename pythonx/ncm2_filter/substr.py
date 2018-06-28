# -*- coding: utf-8 -*-


class Filter:

    def smart_case_match(self, b: str, w: str, e):
        if len(b) > len(w):
            return False

        if len(b) == 0:
            e['user_data']['word_highlight'] = []
            return True

        lw = len(w)
        lb = len(b)
        for i in range(lw - lb + 1):
            match = True
            sw = w[i: i+lb]
            for cb, cw in zip(b, sw):
                if cb == cw:
                    continue
                if cb.lower() != cw.lower():
                    match = False
                    break
                if cb.islower():
                    continue
                else:
                    match = False
                    break
            if match:
                e['user_data']['word_highlight'] = [[i, i+lb]]
                return True

        return False

    def case_match(self, b: str, w: str, e):
        i = w.find(b)
        if i == -1:
            return False
        e['user_data']['word_highlight'] = [[i, i+len(b)]]

    def __init__(self, c='smartcase'):
        if c == 'smartcase':
            self._match = lambda b, w, e: self.smart_case_match(b, w, e)
        elif c == 'icase':
            self._match = lambda b, w, e: self.case_match(
                b.lower(), w.lower(), e)
        else:
            self._match = lambda b, w, e: self.case_match(b, w, e)

    def filter(self, base, matches):
        ret = []
        for m in matches:
            w = m['word']
            if self._match(base, w, m):
                ret.append(m)
        return ret
