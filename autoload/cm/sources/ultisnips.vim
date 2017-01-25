
func! cm#sources#ultisnips#cm_refresh(ctx) dict

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
	let l:typed = strpart(getline('.'), 0, l:col)

	if has_key(l:snips,l:typed)
		" python's `#!` is a snippet
		" this block handles this kind of special case
		let l:matches = [ {"word":l:typed,"dup":1,"icase":1,"menu": "Snips: " . l:snips[l:typed]} ]
		let l:startcol = 1
		call cm#complete(self, a:ctx, l:startcol, l:matches)
		return
	endif

	let l:kw = matchstr(l:typed,'\v\k+$')
	let l:kwlen = len(l:kw)
	if l:kwlen<2
		return
	endif

	" since the available snippet list is fairly small, we can simply dump the
	" whole available list, leave the filtering work to cm's standard filter.
	" This would reduce the work done by vimscript.
	let l:matches = map(keys(l:snips),'{"word":v:val,"dup":1,"icase":1,"menu": "Snips: " . l:snips[v:val]}')
	let l:startcol = l:col - l:kwlen

	" notify the completion framework
	call cm#complete(self, a:ctx, l:startcol, l:matches)

endfunc

