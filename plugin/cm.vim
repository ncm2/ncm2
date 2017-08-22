
if !has('nvim') && v:version<800
	finish
endif

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

let g:cm_matcher = get(g:,'cm_matcher',{'module': 'cm_matchers.prefix_matcher', 'case': 'smartcase'})

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

" Wait for an interval before candidate calculation, to improve editor
" performance for fast typing.
let g:cm_complete_start_delay = get(g:,'cm_complete_start_delay', 0)

" Wait for an interval before popping up, in milliseconds, this would reduce
" the popup menu flickering when multiple sources are updating the popup menu
" in a short interval, use an interval long enough for computer and short
" enough for human
" The name cm_complete_delay is deprecated
let g:cm_complete_popup_delay = get(g:, 'cm_complete_popup_delay', get(g:, 'cm_complete_delay', 50))

" Automatically enable all registered sources by default. Set it to 0 if you
" want to manually enable the registered sources you want by
" g:cm_sources_override.
let g:cm_sources_enable = get(g:,'cm_sources_enable',1)

" used to override default options of sources
let g:cm_sources_override = get(g:,'cm_sources_override',{})

" format: [ (minimal priority, min length), ()]
" the name cm_refresh_default_min_word_len is deprecated, it will be removed
" in the future
let g:cm_refresh_length = get(g:, 'cm_refresh_length', get(g:, 'cm_refresh_default_min_word_len', [[1, 4], [7, 3]]))

let g:cm_completeopt=get(g:,'cm_completeopt','menu,menuone,noinsert,noselect')

" runs after snippet plugin is loaded
func! s:snippet_init()
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
	if !exists('g:cm_completed_snippet_engine')
        let g:cm_completed_snippet_engine = ''
    endif
endfunc

au User CmSetup call s:snippet_init()

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
        \ 'word_pattern': '[\w\-]+',
        \ 'cm_refresh_patterns':['[\w\-]+\s*:\s+'],
        \ 'cm_refresh': {'omnifunc': 'csscomplete#CompleteCSS'},
        \ })

func! s:startup(...)
    if get(g:,'cm_smart_enable',1)
        call cm#_auto_enable_check()
        augroup cm_smart_enable
            au!
            au BufEnter * call cm#_auto_enable_check()
            au OptionSet buftype call cm#_auto_enable_check()
        augroup end
    endif
endfunc

call timer_start(get(g:, 'cm_startup_delay', 100), function('s:startup'))
