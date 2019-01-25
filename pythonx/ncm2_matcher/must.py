from ncm2 import matcher_get, matcher_opt_formalize

def Matcher(**kargs):
    matchers = []

    opts = kargs['matchers']
    context = kargs['context']

    default_params = kargs.copy()
    del default_params['matchers']
    del default_params['context']
    del default_params['name']

    for opt in opts:
        tmp = default_params.copy()
        opt = matcher_opt_formalize(opt)
        tmp.update(opt)
        matcher = matcher_get(context, tmp)
        matchers.append(matcher)

    def match(b, m):
        for matcher in matchers:
            if not matcher(b, m):
                return False
        return True

    return match
