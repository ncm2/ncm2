
" if you don't want built-in sources enabled
" use `let g:cm_builtin_sources={}`
let s:cm_builtin_sources = get(g:, 'cm_builtin_sources',{'ultisnips':{}})

if has_key(s:cm_builtin_sources,'ultisnips')
	call cm#sources#ultisnips#init()
endif

if get(g:,'cm_enable_for_all',1)
	au BufNew,BufNewFile,BufReadPost * call cm#enable_for_buffer()
endif

