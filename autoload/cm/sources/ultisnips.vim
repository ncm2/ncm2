
" If you're implementing your own completion source, add the setup code like
" this into your vimrc, or plugin/ultisnips.vim
"
"	" use did_plugin_ultisnips to detect the installation of ultisnips
"	" https://github.com/SirVer/ultisnips/blob/76ebfec3cf7340a1edd90ea052b16910733c96b0/autoload/UltiSnips.vim#L1
"	au User CmSetup if exists('did_plugin_ultisnips') | call cm#register_source({'name' : 'cm-ultisnips',
"			\ 'priority': 7, 
"			\ 'abbreviation': 'Snip',
"			\ 'word_pattern': '\S+',
"			\ 'cm_refresh_patterns':['(\S{3,})$'],
"			\ 'cm_refresh': 'cm#sources#ultisnips#cm_refresh',
"			\ }) | endif
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
	let l:snips = UltiSnips#SnippetsInCurrentScope()

	" The available snippet list is fairly small, simply dump the whole list
	" here, leave the filtering work to NCM's standard filter.  This would
	" reduce the work done by vimscript.
	let l:matches = map(keys(l:snips),'{"word":v:val, "dup":1, "icase":1, "info": l:snips[v:val], "is_snippet": 1}')

	" call cm#complete to notify the completion framework for update.
	"
	" Note: If the matches calculation takes a bit long to finish, you should
	" use neovim's job-control (`helo job-control`) api to implement async
	" support, and call cm#complete after the job has finished, instead of
	" doing the whole bunch of work in the same cm_refresh handler. Otherwise
	" it will block neovim's ui, since vimscript is single-threaded.
	"
	" Read more information on `:help cm#complete()`
	"
	call cm#complete(a:opt, a:ctx, a:ctx['startcol'], l:matches)

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

	" notify the completion framework
    call cm#sources#ultisnips#cm_refresh('cm-ultisnips', l:ctx)
    return ''
endfunc

