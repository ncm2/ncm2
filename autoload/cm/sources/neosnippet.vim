
function! cm#sources#neosnippet#cm_refresh(info, ctx)
	let l:snips = values(neosnippet#helpers#get_completion_snippets())
	let l:matches = map(l:snips, '{"word":v:val["word"], "dup":1, "icase":1, "menu": "Snip: " . v:val["menu_abbr"], "is_snippet": 1}')
	call cm#complete(a:info, a:ctx, a:ctx['startcol'], l:matches)
endfunction

" inoremap <silent> <c-k> <c-r>=cm#sources#neosnippet#trigger_or_popup("\<Plug>(neosnippet_expand_or_jump)")<cr>
func! cm#sources#neosnippet#trigger_or_popup(trigger_key)
	let l:ctx = cm#context()

	let l:typed = l:ctx['typed']
	let l:kw = matchstr(l:typed,'\v\S+$')
	if len(l:kw)
		call feedkeys(a:trigger_key)
		return ''
	endif

	" notify the completion framework
	call cm#sources#neosnippet#cm_refresh('cm-neosnippet', l:ctx)
	return ''
endfunc

