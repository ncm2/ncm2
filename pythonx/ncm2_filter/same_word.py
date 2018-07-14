
def Filter(**kargs):
    def filt(data, sr, sctx, sccol, matches):
        res = []
        typed = data['context']['typed']
        for m in matches:
            ud = m['user_data']
            mccol = ud.get('startccol', sccol)
            base = typed[mccol - 1:]
            if base == m['word']:
                continue
            res.append(m)
        return res
    return filt
