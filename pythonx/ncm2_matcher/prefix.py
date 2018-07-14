# -*- coding: utf-8 -*-


def Matcher(case='smartcase', key='abbr', **kargs):

    def match_case(b, m):
        lb = len(b)
        w = m[key][ : lb]
        if b != w:
            return False
        m['user_data']['match_key'] = key
        m['user_data']['match_highlight'] = [[0, lb]]
        return True

    def match_icase(b, m):
        lb = len(b)
        w = m[key][ : lb]
        if b.lower() != w.lower():
            return False
        m['user_data']['match_key'] = key
        m['user_data']['match_highlight'] = [[0, lb]]
        return True

    def match_smart_case(b, m):
        lb = len(b)
        w = m[key][ : lb]

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

        m['user_data']['match_key'] = key
        m['user_data']['match_highlight'] = [[0, lb]]
        return True

    if case == 'smartcase':
        return match_smart_case
    elif case == 'icase':
        return match_icase
    else:
        return match_case
