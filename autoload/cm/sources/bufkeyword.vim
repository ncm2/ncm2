
func! cm#sources#bufkeyword#init()
	if v:vim_did_enter
		call s:init()
	else
		au VimEnter * call s:init()
	endif
endfunc

let s:bufkeyword = {
			\ 'name' : 'cm-bufkeyword',
			\ 'priority': 5, 
			\ 'abbreviation': 'Word',
			\ 'refresh': 0, 
			\ 'channels': [
			\   {'type': 'python3', 'path': 'autoload/cm/sources/bufkeyword.py'}
			\ ],
			\ }

let s:lasttick = ''

func! s:tick()
	return bufnr('%') . '-' . b:changedtick
endfunc

func! s:bufkeyword.refresh_keyword()
	let l:channel = self['channels'][0]
	if !has_key(l:channel,'id')
		return
	endif
	let l:tick = s:tick()
	if s:lasttick!=l:tick
		let s:lasttick = l:tick
		call rpcnotify(l:channel['id'],'refresh_keyword')
	endif
endfunc

func! s:bufkeyword.refresh_keyword_incr()
	let l:channel = self['channels'][0]
	if !has_key(l:channel,'id')
		return
	endif
	let l:tick = s:tick()
	if s:lasttick!=l:tick
		let s:lasttick = l:tick
		call rpcnotify(l:channel['id'],'refresh_keyword_incr',getline('.'))
	endif
endfunc

func! s:init()
	augroup cm_bufkeyword
		autocmd!
		autocmd CursorHold,CursorHoldI,BufEnter,BufWritePost * call s:bufkeyword.refresh_keyword()
		autocmd InsertCharPre * if !(v:char=~'\k') | call s:bufkeyword.refresh_keyword_incr() | end
	augroup end
	call cm#register_source(s:bufkeyword)
endfunc

