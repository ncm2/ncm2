
" omni completion wrapper for cm_refresh
func! ncm2#omni#complete(opt, ctx)
    " omni function's startcol is zero based, convert it to one based
    let l:startcol = call(a:opt['cm_refresh']['omnifunc'],[1,'']) + 1
    let l:typed = a:ctx['typed']
    let l:base = l:typed[l:startcol-1:]
    let l:matches = call(a:opt['cm_refresh']['omnifunc'],[0, l:base])
    if type(l:matches)!=type([])
        return
    endif
    " echom a:opt['name'] . ", col: " . l:startcol . " matches: " . json_encode(l:matches)
    " there's no scoping context in omnifunc, use ncm2#context to get the root
    " context
    call ncm2#complete(a:opt, ncm2#context(), l:startcol, l:matches)
endfunc

