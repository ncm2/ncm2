import re
from functools import reduce


def chcmp_smartcase(a, b): return a == b if a.isupper() else a == b.lower()


def chcmp_case(a, b): return a == b


def chcmp_icase(a, b): return a.lower() == b.lower()


def get_abbrev(s):
    res = []
    if len(s) == 0:
        return res
    # always append 0 so that it should also detects prefix match
    res.append(0)
    for i in range(1, len(s)):
        cp = s[i - 1]
        c = s[i]
        if not c.isalpha():
            if c.isdecimal() and not cp.isdecimal():
                res.append(i)
            continue
        elif not cp.isalpha():
            res.append(i)
            continue
        elif c.isupper() and not cp.isupper():
            res.append(i)
            continue
        else:
            continue
    return res


def fuzzy_match(b, s, chcmp):
    if len(b) == 0:
        return []

    abbr = get_abbrev(s)
    abbr.append(len(s))
    sections = []
    for i in range(len(abbr) - 1):
        sections.append([abbr[i], abbr[i + 1]])

    highlights = substr_fuzzy_match(sections, b, s, chcmp)
    if not highlights:
        return None

    # merge some of the substr fuzzy match
    i = 1
    while i < len(highlights):
        phl = highlights[i - 1]
        blen = phl[1] - phl[0]
        bstart = reduce(lambda x, y: x + y[1] - y[0], highlights[: i - 1], 0)
        # print("bstart %s, blen %s" % (bstart, blen))
        hl = highlights[i]
        if str_match(b[bstart: bstart+blen], s[hl[0] - blen: hl[0]], chcmp):
            # merge
            highlights = highlights[: i-1] + \
                [[hl[0] - blen, hl[1]]] + highlights[i + 1:]
            i -= 1
            continue
        else:
            i += 1

    # TODO check for greater substr meatch in the rest ???

    return highlights


def str_match(b, s, chcmp):
    if len(b) != len(s):
        return False
    for c1, c2 in zip(b, s):
        if not chcmp(c1, c2):
            return False
    return True


def substr_fuzzy_match(sections, b, s, chcmp):
    highlights = []
    last_end = 0
    for sec in sections:
        if sec[0] < last_end:
            continue
        pos, l = max_substr_match(b, s, sec, chcmp)
        if not l:
            continue
        last_end = pos + l
        highlights.append([pos, last_end])
        b = b[l:]
        if not b:
            return highlights
    return None


def max_substr_match(b, s, sec, chcmp):
    max_i = 0
    max_l = 0
    for i in range(sec[0], sec[1]):
        l = 0
        for c1, c2 in zip(b, s[i:]):
            if chcmp(c1, c2):
                l += 1
            else:
                break
        if l > max_l:
            max_l = l
            max_i = i
    return max_i, max_l


def Matcher(case='smartcase', key='abbr', **kargs):

    if case == 'smartcase':
        chcmp = chcmp_smartcase
    elif case == 'icase':
        chcmp = chcmp_icase
    else:
        chcmp = chcmp_case

    def match(b, m):
        hl = fuzzy_match(b, m[key], chcmp)
        if hl is None:
            return False
        m['user_data']['match_key'] = key
        m['user_data']['match_highlight'] = hl
        return True

    return match


def test_fuzzy_match(b, s, chcmp):
    print('base : ' + b)

    res = get_abbrev(s)
    ls = [' '] * len(s)
    for i in res:
        ls[i] = '^'
    print('str  : ' + s)
    print('split: ' + ''.join(ls))

    highlights = fuzzy_match(b, s, chcmp)
    print('       ' + s)
    s2 = ' ' * len(s)
    if highlights:
        for hl in highlights:
            s2 = s2[: hl[0]] + ('^' * (hl[1] - hl[0])) + s2[hl[1]:]
    print('match: ' + s2)


if __name__ == '__main__':
    test_fuzzy_match('subfuzzy', 'substr_fuzzy_match', chcmp_smartcase)
    print('')
    test_fuzzy_match('substrfuzzy', 'substr_substrfuzzy_match', chcmp_smartcase)
    print('')
    test_fuzzy_match('sfum', 'substr_substrfuzzy_match', chcmp_smartcase)
    print('')
