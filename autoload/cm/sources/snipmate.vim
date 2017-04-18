
function! cm#sources#snipmate#cm_refresh(info, ctx)
	let l:word    = snipMate#WordBelowCursor()
	let l:matches = map(snipMate#GetSnippetsForWordBelowCursorForComplete(''),'extend(v:val,{"dup":1})')
	call cm#complete(a:info['name'], a:ctx, a:ctx['col']-len(l:word), l:matches)
endfunction

" inoremap <silent> <c-u> <c-r>=cm#sources#snipmate#trigger_or_popup("\<Plug>snipMateTrigger")<cr>
func! cm#sources#snipmate#trigger_or_popup(trigger_key)

	let l:word    = snipMate#WordBelowCursor()
	if len(l:word)
		call feedkeys(a:trigger_key)
		return ''
	endif

	let l:ctx = cm#context()
	call cm#complete('cm-snipmate', l:ctx, l:ctx['col']-len(l:word), snipMate#GetSnippetsForWordBelowCursorForComplete(''))
	return ''
endfunc

