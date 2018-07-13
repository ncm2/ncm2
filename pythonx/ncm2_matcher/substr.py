# -*- coding: utf-8 -*-


class Matcher:

    def __init__(self, c='smartcase', key='abbr'):
        self.key = key
        if c == 'smartcase':
            self.match = self.match_smart_case
        elif c == 'icase':
            self.match = self.match_icase
        else:
            self.match = self.match_case

    def match_smart_case(self, b, e):
        w = e[self.key]

        lw = len(w)
        lb = len(b)

        if lb > lw:
            return False

        if not lb:
            e['user_data']['match_highlight'] = []
            return True

        for i in range(lw - lb + 1):
            match = True
            sw = w[i: i + lb]
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
                e['user_data']['match_key'] = self.key
                e['user_data']['match_highlight'] = [[i, i + lb]]
                return True

        return False

    def match_case(self, b, e):
        w = e[self.key]
        i = w.find(b)
        if i == -1:
            return False
        e['user_data']['match_key'] = self.key
        e['user_data']['match_highlight'] = [[i, i + len(b)]]

    def match_icase(self, b, e):
        w = e[self.key]
        i = w.lower().find(b.lower())
        if i == -1:
            return False
        e['user_data']['match_key'] = self.key
        e['user_data']['match_highlight'] = [[i, i + len(b)]]
