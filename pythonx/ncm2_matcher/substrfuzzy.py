import re
from functools import reduce


def chcmp_smartcase(a, b): return a == b if a.isupper() else a == b.lower()


def chcmp_case(a, b): return a == b


def chcmp_icase(a, b): return a.lower() == b.lower()


def fuzzy_match(b, s, chcmp):
    if len(b) == 0:
        return []
    if len(s) == 0:
        return None
    abbrs = get_abbrev(s)
    return substr_fuzzy_match(b, s, abbrs, chcmp)


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


def abbrs_ge(abbrs, ge):
    for i, e in enumerate(abbrs):
        if e >= ge:
            return abbrs[i:]
    return []


def substr_fuzzy_match(b, s, abbrs, chcmp):
    end = len(s)
    start = abbrs[0]
    while end > start:
        pos, l = max_substr_match(b, s, [start, end], chcmp)
        if not l:
            return None
        highlight = [pos, pos + l]
        if l == len(b):
            return [highlight]
        sub_abbrs = abbrs_ge(abbrs, pos + l)
        if sub_abbrs:
            highlights = substr_fuzzy_match(b[l:], s, sub_abbrs, chcmp)
            if highlights:
                return [highlight] + highlights
        if l == 1:
            # no more fallback
            return None
        end = pos
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
        ls[i] = '|'
    print('split: ' + ''.join(ls))
    print('str  : ' + s)

    highlights = fuzzy_match(b, s, chcmp)
    s2 = ' ' * len(s)
    if highlights:
        for hl in highlights:
            s2 = s2[: hl[0]] + ('^' * (hl[1] - hl[0])) + s2[hl[1]:]
    else: 
        s2 = '-' * len(s)
    print('match: ' + s2)


if __name__ == '__main__':
    test_fuzzy_match('subfuzzy', 'substr_fuzzy_match', chcmp_smartcase)
    print('')
    test_fuzzy_match(
        'substrfuzzy', 'substr_substrfuzzy_match', chcmp_smartcase)
    print('')
    test_fuzzy_match('sfum', 'substr_substrfuzzy_match', chcmp_smartcase)
    print('')
    test_fuzzy_match('sfuym', 'substr_substrfuzzy_match', chcmp_smartcase)
    print('')
    test_fuzzy_match('abcfoo', 'abc_foo_abcf', chcmp_smartcase)
    print('')
    test_fuzzy_match('abcfoo', 'a_b_c_abc_abfoo', chcmp_smartcase)
    print('')
