# -*- coding: utf-8 -*-


def Matcher(context, case='smartcase', key='abbr', **kargs):

    # this matcher does not allow inc_match
    context['inc_match'] = 0

    def match_smart_case(b, e):
        w = e[key]

        lw = len(w)
        lb = len(b)

        if lb != lw:
            return False

        for cb, cw in zip(b, w):
            if cb == cw:
                continue
            if cb.lower() != cw.lower():
                return False
            if cb.islower():
                continue
            else:
                return False

        e['user_data']['match_key'] = key
        e['user_data']['match_highlight'] = [[0, len(b)]]
        return True

    def match_case(b, e):
        w = e[key]
        if b != w:
            return False
        e['user_data']['match_key'] = key
        e['user_data']['match_highlight'] = [[0, len(b)]]
        return True

    def match_icase(b, e):
        w = e[key]
        if b.lower() != w.lower():
            return False
        e['user_data']['match_key'] = key
        e['user_data']['match_highlight'] = [[0, len(b)]]
        return True

    if case == 'smartcase':
        return match_smart_case
    elif case == 'icase':
        return match_icase
    else:
        return match_case

