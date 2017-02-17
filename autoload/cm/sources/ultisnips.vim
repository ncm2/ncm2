

" If you're implementing your own completion source, add the setup code like
" this into your vimrc, or plugin/foo.vim
"
"     autocmd User CmSetup call cm#register_source({'name' : 'cm-ultisnips',
"		    \ 'priority': 7, 
"		    \ 'abbreviation': 'Snips',
"		    \ 'cm_refresh': 'cm#sources#ultisnips#cm_refresh',
"		    \ })
"
" An autocmd will avoid error when nvim-completion-manager is not installed
" yet. And it also avoid the loading of autoload/cm.vim on neovim startup, so
" that nvim-completion-manager won't affect neovim's startup time.
"
func! cm#sources#ultisnips#cm_refresh(opt,ctx)

	if get(s:, 'disable', 0)
		return
	endif

	try
		" UltiSnips#SnippetsInCurrentScope
		" {
		"     "modeline": "Vim modeline",
		"     "au": "augroup ... autocmd block",
		"     ......
		" }
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

	" The available snippet list is fairly small, simply dump the whole list
	" here, leave the filtering work to cm's standard filter.  This would
	" reduce the work done by vimscript.
	let l:matches = map(keys(l:snips),'{"word":v:val,"dup":1,"icase":1,"info": l:snips[v:val]}')

	" startcol is one-based
	let l:startcol = l:col - l:kwlen

	" call cm#complete to notify the completion framework for update.
	"
	" Note: If the matches calculation takes a bit long to finish, you should
	" use neovim's job-control (`helo job-control`) api to implement async
	" support, and call cm#complete after the job has finished, instead of
	" doing the whole bunch of work in the same cm_refresh handler. Otherwise
	" it will block neovim's ui, since vimscript is single-threaded.
	"
	" The `a:opt` here tells the manager to identify the source. You may also
	" use `a:opt['name']` or simply `'cm-ultisnips'` as the name of the
	" source.
	"
	"     cm#complete('cm-ultisnips', a:ctx, l:startcol, l:matches)
	"
	" The `a:ctx` tells completion manager which cm_refresh request you are
	" responding to. If the user type more words before you call cm#complete,
	" the manager will ignore this call since `a:ctx` is outdated.  And the
	" manager will send a new cm_refresh request to the handler.
	"
	" If the list it not complete, further typing results in recomputing this
	" list, you should append an extra `1` as the 5-th parameter. Then the
	" manager will not cache the result, and send a new cm_refresh request for
	" futher typing.
	"
	"     cm#complete(a:opt, a:ctx, l:startcol, l:matches, 1)
	"
	" For more information on `startcol` and `matches`, please refer to `:help
	" complete()`. They are used in the same way as vim's
	" `complete({startcol}, {matches})` function.
	"
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

