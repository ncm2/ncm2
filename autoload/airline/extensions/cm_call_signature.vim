
" TODO: syntax highlighting support

let s:spc = g:airline_symbols.space

let g:airline#extensions#cm_call_signature#enabled = get(g:,'airline#extensions#cm_call_signature#enabled',0)

function! airline#extensions#cm_call_signature#init(ext)
	call airline#parts#define_raw('call_signature', '%{airline#extensions#cm_call_signature#get()}')
	call a:ext.add_statusline_func('airline#extensions#cm_call_signature#apply')
endfunction

" define status line structure
function! airline#extensions#cm_call_signature#apply(...)
	if g:airline#extensions#cm_call_signature#enabled==0
		return
	endif

	" call airline#update_statusline() 
	" if get(b:,'airline_cm_signature','') changed
	if get(b:,'airline_cm_signature','')!=''
		let l:airline_section_c = s:spc.g:airline_left_alt_sep.s:spc.'%#__accent_red#%{airline#extensions#cm_call_signature#get()}%#__restore__#'
		call airline#extensions#append_to_section('c', l:airline_section_c)
	endif

endfunction

function! airline#extensions#cm_call_signature#get()
	return get(b:,'airline_cm_signature','')
endfunction

function! airline#extensions#cm_call_signature#set(val)
	if g:airline#extensions#cm_call_signature#enabled==0
		return
	endif
	if get(b:,'airline_cm_signature','')=='' && a:val!=''
		" change the status line structure
		let b:airline_cm_signature = a:val
		call airline#update_statusline()
	elseif get(b:,'airline_cm_signature','')!='' && a:val==''
		" change the status line structure
		let b:airline_cm_signature = a:val
		call airline#update_statusline()
	else
		" change the value only
		let b:airline_cm_signature = a:val
	endif
endfunction
