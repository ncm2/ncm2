import re

chcmp_smartcase = lambda a,b: a == b if a.isupper() else a == b.lower()
chcmp_case = lambda a,b: a == b
chcmp_icase = lambda a,b: a.lower() == b.lower()

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
    return abbr_fuzzy_match(abbr, b, s, 0, chcmp)

def abbr_fuzzy_match(abbr, b, s, off, chcmp):
    for i, p in enumerate(abbr):
        p = p - off
        if p < 0:
            continue
        mcp = max_common_prefix(b, s[p:], chcmp)
        if len(mcp) == len(b):
            return [[off + p, off + p + len(mcp)]]
        # # max(mcpl-3, 0) don't fallback too deep for performance
        mcpl = len(mcp)
        for l in range(mcpl, 0, -1):
            b2 = b[l:]
            s2 = s[p + l:]
            m = abbr_fuzzy_match(abbr[i+1:], b2, s2, off + p + l, chcmp)
            if m:
                return [[off + p, off + p + l]] + m
    return None

def max_common_prefix(b, s, chcmp):
    l = 0
    for c1, c2 in zip(b, s):
        if chcmp(c1, c2):
            l += 1
        else:
            break
    return b[:l]

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

def test_abbrev(s):
    res = get_abbrev(s)
    ls = [' '] * len(s)
    for i in res:
        ls[i] = '^'
    print(s)
    print(''.join(ls))

def test():
    s = 'abbr_fuzzy_match'
    b = 'abbrfuzzy'
    test_abbrev(s)
    print(fuzzy_match(b, s, chcmp_smartcase))
    print(max_common_prefix(b, s, chcmp_smartcase))

if __name__  == '__main__':
    test()
