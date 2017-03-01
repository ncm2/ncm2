

let g:cm_buffer_size_limit = get(g:,'cm_buffer_size_limit',1000000)

if get(g:,'cm_enable_for_all',1)
	" simple ignore files larger than 1M, for performance
	au BufWinEnter * if (exists('b:cm_enable')==0 && line2byte(line("$") + 1)<g:cm_buffer_size_limit) | call cm#enable_for_buffer() | endif

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


au User CmSetup call cm#register_source({'name' : 'cm-ultisnips',
		\ 'priority': 7, 
		\ 'abbreviation': 'Snip',
		\ 'cm_refresh_patterns':['\S{1,}$'],
		\ 'cm_refresh': 'cm#sources#ultisnips#cm_refresh',
		\ })

" css
" the omnifunc pattern is PCRE
au User CmSetup call cm#register_source({'name' : 'cm-css',
		\ 'priority': 9, 
		\ 'scoping': 1,
		\ 'scopes': ['css','scss'],
		\ 'abbreviation': 'css',
		\ 'cm_refresh_patterns':['\w{3,}$',':\s+(\w*)$'],
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

