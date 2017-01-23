
let s:name = 'cm-ultisnips'

func! cm#sources#ultisnips#init()

	augroup cm_ultisnips

		" autocmd TextChangedI * call s:on_cursor_moved_i()
		" use PossibleTextChangedI provided by https://github.com/roxma/nvim-possible-textchangedi
		autocmd User PossibleTextChangedI call s:on_cursor_moved_i()

	augroup end

	" you need to register this source
	call cm#register_source({'name' : s:name, 'priority': 6, 'abbreviation': 'ultisnips'})

endfunc

func! s:on_cursor_moved_i()


	" UltiSnips#SnippetsInCurrentScope
	" {
	"     "modeline": "Vim modeline",
	"     "au": "augroup ... autocmd block",
	"     ......
	" }

	if get(s:, 'disable', 0)
		return
	endif

	try
		let l:snips = UltiSnips#SnippetsInCurrentScope()
	catch
		" guess that ultisnips is not available
		if get(s:, 'disable', -1)==-1
			let s:disable =1
		endif
		return
	endtry
	" guess that ultisnips is available
	let s:disable = 0

	let l:matches = []

	let l:col = col('.')
	let l:txt = strpart(getline('.'), 0, l:col)
	let l:kw = matchstr(l:txt,'\v\k+$')

	let l:kwlen = len(l:kw)
	if l:kwlen>=2
		for l:name in keys(l:snips)
			if l:name[0:l:kwlen-1] == l:kw
				let l:matches = add(l:matches, l:name)
			endif
		endfor
	endif

	if empty(l:matches)

		if has_key(l:snips,l:txt)
			" python's `#!` is a snippet
			" this block handles this kind of special case
			let l:matches = [ l:txt ]
			let l:startcol = 1
		else
			return
		endif

	else
		let l:startcol = l:col - l:kwlen
	endif

	" notify the completion framework after gathering matches calculation
	call cm#complete(s:name, cm#context(), l:startcol, l:matches)

endfunc

