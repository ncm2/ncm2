
" omni completion wrapper for cm_refresh
func! ncm2#omni#complete(funcname, ctx)
    " omni function's startbcol is zero based, convert it to one based
    let startbcol = call(a:funcname, [1,'']) + 1
    let typed = a:ctx['typed']
    let base = typed[startbcol - 1: ]
    let matches = call(a:funcname, [0, base])
    if type(matches)!=type([])
        return
    endif

    " convert startbcol -> startccol
    if startbcol == 1
        let startccol = 1
    else
        let tmp = typed[: startbcol - 2]
        let startccol = strchars(tmp) + 1
    endif

    " omnifunc doesn't know anything about subscope
    " hack scope_ccol sot that it won't be adjusted by ncm2_core
    let a:ctx.scope_ccol = 1

    call ncm2#complete(a:ctx, startccol, matches)
endfunc

