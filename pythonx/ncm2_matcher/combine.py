from ncm2 import matcher_get, matcher_opt_formalize
from copy import deepcopy

def Matcher(**kargs):
    opts = kargs['matchers']
    matchers = []

    default_params = deepcopy(kargs)
    del default_params['matchers']

    for opt in opts:
        tmp = deepcopy(default_params)
        opt = matcher_opt_formalize(opt)
        tmp.update(opt)
        matcher = matcher_get(tmp)
        matchers.append(matcher)

    def match(b, m):
        for matcher in matchers:
            if matcher(b, m):
                return True
        return False

    return match
