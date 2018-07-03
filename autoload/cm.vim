" fake NCM api for LanguageClient-neovim working on ncm2
"
" need vimrc
"   let g:cm_matcher = {'module': 'cm_matchers.prefix_matcher', 'case': 'smartcase'}
" to trick LanguageClient-neovim to believe that ncm is available.

func! s:rename(sr, old, cur)
    if has_key(a:sr, a:old) && !has_key(a:sr, a:cur) 
        let a:sr[a:cur] = a:sr[a:old]
    endif
endfunc

func! cm#register_source(sr)
    echom 'register source' . json_encode(a:sr)
    call s:rename(a:sr, 'scopes', 'scope')
    call s:rename(a:sr, 'cm_refresh_patterns', 'complete_pattern')
    call s:rename(a:sr, 'abbreviation', 'mark')
    let a:sr.early_cache = 0
    if has_key(a:sr, 'cm_refresh') && !has_key(a:sr, 'on_complete')
        let a:sr['on_complete'] = 'cm#_on_complete'
    endif
    call ncm2#register_source(a:sr)
endfunc

func! cm#_on_complete(ctx) dict
    let d = deepcopy(self)
    let enc = json_encode(a:ctx)
    let d.cm_refresh_length = 3
    let d.sort = 1
    let a:ctx.startcol = a:ctx.startccol
    let a:ctx.col = a:ctx.ccol
    let a:ctx.force = 0
    let a:ctx.scope_match = enc
    call call(self.cm_refresh, [d, a:ctx], self)
endfunc

func! cm#complete(info, ctx, startcol, matches, is_incomplete)
    let startccol = a:startcol
    let a:ctx.source = a:ctx.scope_match
    call ncm2#complete(json_decode(a:ctx.scope_match), startccol, a:matches, a:is_incomplete)
endfunc

