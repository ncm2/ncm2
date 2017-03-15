
" simply ignore files larger than 1M, for performance
let g:cm_buffer_size_limit = get(g:,'cm_buffer_size_limit',1000000)

" multithreadig, saves more memory, enabled by default
if !exists('g:cm_multi_threading')
	if $NVIM_NCM_MULTI_THREAD == ''
		let g:cm_multi_threading = 1
	else
		let g:cm_multi_threading = $NVIM_NCM_MULTI_THREAD
	endif
endif

if get(g:,'cm_smart_enable',1)

	au BufWinEnter * call cm#_auto_enable_check()
	" Unite's `buftype` is not set when BufWinEnter is triggered, use this as
	" workaround
	au OptionSet buftype call cm#_auto_enable_check()

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
let g:cm_complete_delay = get(g:,'cm_complete_delay',80)

" Automatically enable all registered sources by default. Set it to 0 if you
" want to manually enable the registered sources you want by
" g:cm_sources_override.
let g:cm_sources_enable = get(g:,'cm_sources_enable',1)

" used to override default options of sources
let g:cm_sources_override = get(g:,'cm_sources_override',{})

" format: [ (minimal priority, min length), ()]
let g:cm_refresh_default_min_word_len = get(g:,'cm_refresh_default_min_word_len',[[1,4],[7,3]])

func! s:lazy_init()
	if !exists('g:cm_completed_snippet_enable')
		if get(g:,'neosnippet#enable_completed_snippet',0)
			let g:cm_completed_snippet_enable = 1
			let g:cm_completed_snippet_engine = 'neosnippet'
		elseif exists('g:did_plugin_ultisnips')
			let g:cm_completed_snippet_enable = 1
			let g:cm_completed_snippet_engine = 'ultisnips'
		elseif exists('g:snipMateSources')
			let g:cm_completed_snippet_enable = 1
			let g:cm_completed_snippet_engine = 'snipmate'
		else
			let g:cm_completed_snippet_enable = 0
			let g:cm_completed_snippet_engine = ''
		endif
	endif
endfunc

au User CmSetup call s:lazy_init()

" use did_plugin_ultisnips to detect the installation of ultisnips
" https://github.com/SirVer/ultisnips/blob/76ebfec3cf7340a1edd90ea052b16910733c96b0/autoload/UltiSnips.vim#L1
au User CmSetup if exists('g:did_plugin_ultisnips') | call cm#register_source({'name' : 'cm-ultisnips',
		\ 'priority': 7, 
		\ 'abbreviation': 'Snip',
		\ 'word_pattern': '\S+',
		\ 'cm_refresh': 'cm#sources#ultisnips#cm_refresh',
		\ }) | endif

au User CmSetup if exists('g:loaded_neosnippet') | call cm#register_source({'name' : 'cm-neosnippet',
		\ 'priority': 7, 
		\ 'abbreviation': 'Snip',
		\ 'word_pattern': '\S+',
		\ 'cm_refresh': 'cm#sources#neosnippet#cm_refresh',
		\ }) | endif

au User CmSetup if exists('g:snipMateSources') | call cm#register_source({'name' : 'cm-snipmate',
		\ 'priority': 7,
		\ 'abbreviation': 'Snip',
		\ 'word_pattern': '\S+',
		\ 'cm_refresh': 'cm#sources#snipmate#cm_refresh',
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

