import re

def Filter(**kargs):
    def filt(data, sr, sctx, sccol, matches):
        ret = []
        seen = {}
        for m in matches:
            # suppress vim's builtin dedup which is based own m['word']
            m['dup'] = 1
            word = m['word']
            arr = seen.setdefault(word, [])
            if arr:
                skip = False
                for m1 in arr:
                    if m1 == m:
                        skip = True
                        break
                if skip:
                    continue
            ret.append(m)
            arr.append(m)
        return ret
    return filt
