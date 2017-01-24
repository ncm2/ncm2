
if get(g:,'cm_enable_for_all',1)
	au BufNew,BufNewFile,BufReadPost * call cm#enable_for_buffer()
endif

" if you don't want built-in sources enabled
" use `let g:cm_builtin_sources={}`
let s:cm_builtin_sources = get(g:, 'cm_builtin_sources',{
		\ 'ultisnips':{},
		\ 'bufkeyword':{},
		\ })

if has_key(s:cm_builtin_sources,'ultisnips')
	call cm#register_source({'name' : 'cm-ultisnips',
		\ 'priority': 6, 
		\ 'abbreviation': 'UltiSnips',
		\ 'refresh': 0, 
		\ 'on_changed': function('cm#sources#ultisnips#on_changed'),
		\ })
endif

" if has_key(s:cm_builtin_sources,'bufkeyword')
" 	call cm#register_source({'name' : 'cm-bufkeyword',
" 		\ 'priority': 5, 
" 		\ 'abbreviation': 'UltiSnips',
" 		\ 'refresh': 0, 
" 		\ 'on_changed': function('cm#sources#ultisnips#on_changed'),
" 		\ })
" endif
" 
