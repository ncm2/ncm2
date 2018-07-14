from ncm2 import matcher_get, matcher_opt_formalize

def Matcher(**kargs):
    opts = kargs['matchers']
    matchers = []

    for opt in opts:
        opt = matcher_opt_formalize(opt)
        matcher = matcher_get(opt)
        matchers.append(matcher)

    def match(b, m):
        for matcher in matchers:
            if matcher(b, m):
                return True
        return False

    return match
