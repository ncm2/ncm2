
func! cm#sources#ultisnips#cm_refresh(opt,ctx)

	let l:snips = UltiSnips#SnippetsInCurrentScope()

	let l:matches = map(keys(l:snips),'{"word":v:val, "dup":1, "icase":1, "info": l:snips[v:val], "is_snippet": 1}')

	call cm#complete(a:opt, a:ctx, a:ctx['startcol'], l:matches)

endfunc


" Tips: Add this to your vimrc for triggering snips popup with <c-u>
"
" let g:UltiSnipsExpandTrigger = "<Plug>(ultisnips_expand)"
" inoremap <silent> <c-u> <c-r>=cm#sources#ultisnips#trigger_or_popup("\<Plug>(ultisnips_expand)")<cr>
"
func! cm#sources#ultisnips#trigger_or_popup(trigger_key)

	let l:ctx = cm#context()

	let l:typed = l:ctx['typed']
	let l:kw = matchstr(l:typed,'\v\S+$')
	if len(l:kw)
		call feedkeys(a:trigger_key)
		return ''
	endif

    let l:ctx['startcol'] = 1
    call cm#sources#ultisnips#cm_refresh('cm-ultisnips', l:ctx)
    return ''
endfunc

