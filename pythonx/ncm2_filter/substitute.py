import re

def Filter(**kargs):
    key = kargs['key']
    pattern = re.compile(kargs['pattern'])
    replace = kargs['replace']
    def filt(data, sr, sctx, sccol, matches):
        for m in matches:
            if key in m:
                m[key] = pattern.sub(replace, m[key])
        return matches
    return filt
