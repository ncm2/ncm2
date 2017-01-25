
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
	let l:txt = strpart(getline('.'), 0, l:col)
	let l:kw = matchstr(l:txt,'\v\k+$')

	let l:kwlen = len(l:kw)
	if l:kwlen>=2
		for l:name in keys(l:snips)
			if l:name[0:l:kwlen-1] == l:kw
				" special hint for ultisnips, use dup=1
				let l:matches = add(l:matches, {'word':l:name,'dup':1})
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

	" echo 'name: ' . self.name
	" notify the completion framework after gathering matches calculation
	call cm#complete(self, a:ctx, l:startcol, l:matches)

endfunc

