
" simply ignore files larger than 1M, for performance
let g:cm_buffer_size_limit = get(g:,'cm_buffer_size_limit',1000000)

if get(g:,'cm_smart_enable',1)

	func! s:auto_enable_check()
		if exists('b:cm_enable') && b:cm_enable!=2
			return
		endif
		if (&buftype=='' &&  line2byte(line("$") + 1)<g:cm_buffer_size_limit) 
			" 2 for auto enable
			call cm#enable_for_buffer(2)
		else
			call cm#disable_for_buffer()
		endif
	endfunc

	au BufWinEnter * call s:auto_enable_check()
	" Unite's `buftype` is not set when BufWinEnter is triggered, use this as
	" workaround
	au OptionSet buftype call s:auto_enable_check()

	" disable clang default mapping by default,
	" https://github.com/Rip-Rip/clang_complete/pull/515
	let g:clang_make_default_keymappings = get(g:,'clang_make_default_keymappings',0)
endif

let g:cm_matcher = get(g:,'cm_matcher',{'module': 'cm_matchers.prefix_matcher', 'case': 'smartcase'})

" use this for fuzzy matching
" let g:cm_matcher = get(g:,'cm_matcher',{'module': 'cm.matchers.fuzzy_matcher', 'case': 'smartcase'})

if !exists('g:cm_completekeys')
	if g:cm_matcher['module'] == 'cm_matchers.prefix_matcher'
		" <Plug>(cm_complete) has no flickering issue with prefix_matcher. But
		" it has terrible popup flickering issue with fuzzy_matcher.
		let g:cm_completekeys = "\<Plug>(cm_complete)"
	else
		" <Plug>(cm_completefunc) has no popup flickering with fuzzy matcher.
		" But it has cursor flickering issue
		let g:cm_completekeys = "\<Plug>(cm_completefunc)"
	endif
endif

let g:cm_auto_popup = get(g:,'cm_auto_popup',1)

" Wait for an interval before popping up, in milliseconds, this would reduce
" the popup menu flickering when multiple sources are updating the popup menu
" in a short interval, use an interval long enough for computer and short
" enough for human
let g:cm_complete_delay = get(g:,'cm_complete_delay',50)

" Automatically enable all registered sources by default. Set it to 0 if you
" want to manually enable the registered sources you want by
" g:cm_sources_override.
let g:cm_sources_enable = get(g:,'cm_sources_enable',1)

" used to override default options of sources
let g:cm_sources_override = get(g:,'cm_sources_override',{})

" format: [ (minimal priority, min length), ()]
let g:cm_refresh_default_min_word_len = get(g:,'cm_refresh_default_min_word_len',[[1,4],[7,3]])

let g:cm_completed_snippet_enable = get(g:,'cm_completed_snippet_enable',get(g:,'neosnippet#enable_completed_snippet',0))

" use did_plugin_ultisnips to detect the installation of ultisnips
" https://github.com/SirVer/ultisnips/blob/76ebfec3cf7340a1edd90ea052b16910733c96b0/autoload/UltiSnips.vim#L1
au User CmSetup if exists('did_plugin_ultisnips') | call cm#register_source({'name' : 'cm-ultisnips',
		\ 'priority': 7, 
		\ 'abbreviation': 'Snip',
		\ 'word_pattern': '\S+',
		\ 'cm_refresh': 'cm#sources#ultisnips#cm_refresh',
		\ }) | endif


" use did_plugin_ultisnips to detect the installation of ultisnips
" https://github.com/SirVer/ultisnips/blob/76ebfec3cf7340a1edd90ea052b16910733c96b0/autoload/UltiSnips.vim#L1
au User CmSetup if exists('g:loaded_neosnippet') | call cm#register_source({'name' : 'cm-neosnippet',
		\ 'priority': 7, 
		\ 'abbreviation': 'Snip',
		\ 'word_pattern': '\S+',
		\ 'cm_refresh': 'cm#sources#neosnippet#cm_refresh',
		\ }) | endif

" css
" the omnifunc pattern is PCRE
au User CmSetup call cm#register_source({'name' : 'cm-css',
		\ 'priority': 9, 
		\ 'scoping': 1,
		\ 'scopes': ['css','scss'],
		\ 'abbreviation': 'css',
		\ 'cm_refresh_patterns':[':\s+\w*$'],
		\ 'cm_refresh': {'omnifunc': 'csscomplete#CompleteCSS'},
		\ })


" " keyword
" call cm#register_source({
" 		\ 'name' : 'cm-bufkeyword',
" 		\ 'priority': 5, 
" 		\ 'abbreviation': 'Key',
" 		\ 'channel': {
" 		\		'type': 'python3',
" 		\		'path': 'autoload/cm/sources/cm_bufkeyword.py',
" 		\		'events':['CursorHold','CursorHoldI','BufEnter','BufWritePost','TextChangedI'],
" 		\		'detach':1,
" 		\ },
" 		\ })

