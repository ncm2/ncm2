# -*- coding: utf-8 -*-


def Matcher(case='smartcase', key='abbr', **kargs):

    def match_smart_case(b, e):
        w = e[key]

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
                e['user_data']['match_key'] = key
                e['user_data']['match_highlight'] = [[i, i + lb]]
                return True

        return False

    def match_case(b, e):
        w = e[key]
        i = w.find(b)
        if i == -1:
            return False
        e['user_data']['match_key'] = key
        e['user_data']['match_highlight'] = [[i, i + len(b)]]
        return True

    def match_icase(b, e):
        w = e[key]
        i = w.lower().find(b.lower())
        if i == -1:
            return False
        e['user_data']['match_key'] = key
        e['user_data']['match_highlight'] = [[i, i + len(b)]]
        return True

    if case == 'smartcase':
        return match_smart_case
    elif case == 'icase':
        return match_icase
    else:
        return match_case

