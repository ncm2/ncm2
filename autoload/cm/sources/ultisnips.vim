
" If you're implementing your own completion source, add the setup code like
" this into your vimrc, or plugin/foo.vim
"
" autocmd User CmSetup call cm#register_source({'name' : 'cm-ultisnips',
"		\ 'priority': 7, 
"		\ 'abbreviation': 'Snips',
"		\ 'cm_refresh': 'cm#sources#ultisnips#cm_refresh',
"		\ })
"
" An autocmd will avoid error when nvim-completion-manager is not installed
" yet. And it also avoid the loading of autoload/cm.vim on neovim startup, so
" that nvim-completion-manager won't affect neovim's startup time.
"



func! cm#sources#ultisnips#cm_refresh(opt,ctx)

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

	let l:col = a:ctx['col']
	let l:typed = a:ctx['typed']

	let l:kw = matchstr(l:typed,'\v\S+$')
	let l:kwlen = len(l:kw)
	if l:kwlen<2 && !has_key(l:snips,l:kw)
		return
	endif

	" since the available snippet list is fairly small, we can simply dump the
	" whole available list, leave the filtering work to cm's standard filter.
	" This would reduce the work done by vimscript.
	let l:matches = map(keys(l:snips),'{"word":v:val,"dup":1,"icase":1,"info": l:snips[v:val]}')
	let l:startcol = l:col - l:kwlen

	" notify the completion framework
	call cm#complete(a:opt, a:ctx, l:startcol, l:matches)

endfunc


"
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

	let l:snips = UltiSnips#SnippetsInCurrentScope()
	let l:matches = map(keys(l:snips),'{"word":v:val,"dup":1,"icase":1,"info": l:snips[v:val]}')
	let l:startcol = l:ctx['col']

	" notify the completion framework
	call cm#complete('cm-ultisnips', l:ctx, l:startcol, l:matches)

	return ''

endfunc

