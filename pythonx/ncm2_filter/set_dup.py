import re

def Filter(**kargs):
    value = kargs['value']
    def filt(data, sr, sctx, sccol, matches):
        for m in matches:
            m['dup'] = value
            print('set_dup.py')
        return matches
    return filt
