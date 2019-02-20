
def Filter(**kargs):
    limit = kargs['limit']
    ellipsis = kargs.get('ellipsis', '...')
    def filt(data, sr, sctx, sccol, matches):
        for m in matches:
            abbr = m['abbr']
            if len(abbr) > limit:
                m['abbr'] = abbr[:limit] + ellipsis
        return matches
    return filt
