# -*- coding: utf-8 -*-


class Matcher:

    def __init__(self, c='smartcase'):
        if c == 'smartcase':
            self.match = self.match_smart_case
        elif c == 'icase':
            self.match = self.match_icase
        else:
            self.match = self.match_case

    def match_case(self, b, m):
        lb = len(b)
        w = m['word'][ : lb]
        if b != w:
            return False
        m['user_data']['match_highlight'] = [[0, lb]]
        return True

    def match_icase(self, b, m):
        lb = len(b)
        w = m['word'][ : lb]
        if b.lower() != w.lower():
            return False
        m['user_data']['match_highlight'] = [[0, lb]]
        return True

    def match_smart_case(self, b, m):
        lb = len(b)
        w = m['word'][ : lb]

        if lb != len(w):
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

        m['user_data']['match_highlight'] = [[0, lb]]
        return True
