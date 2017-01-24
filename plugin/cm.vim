
if get(g:,'cm_enable_for_all',1)
	au BufEnter * if exists('b:cm_enable')==0 | call cm#enable_for_buffer() | endif
endif

" if you don't want built-in sources enabled
" use `let g:cm_builtin_sources={}`
let s:cm_builtin_sources = get(g:, 'cm_builtin_sources',{
		\ 'ultisnips':{},
		\ 'bufkeyword':{},
		\ 'jedi':{},
		\ })


" ultisnips
if has_key(s:cm_builtin_sources,'ultisnips')
	call cm#register_source({'name' : 'cm-ultisnips',
		\ 'priority': 7, 
		\ 'abbreviation': 'UltiSnips',
		\ 'refresh': 0, 
		\ 'on_changed': function('cm#sources#ultisnips#on_changed'),
		\ })
endif


" keyword
if has_key(s:cm_builtin_sources,'bufkeyword')
	call cm#sources#bufkeyword#init()
endif


" jedi
if has_key(s:cm_builtin_sources,'jedi')
	au FileType python if has_key(s:cm_builtin_sources,'jedi') | call cm#register_source({
			\ 'name' : 'cm-jedi',
			\ 'priority': 9, 
			\ 'abbreviation': 'Jedi',
			\ 'refresh': 0, 
			\ 'channels': [
			\   {'type': 'python3', 'path': 'autoload/cm/sources/cm_jedi.py'}
			\ ],
			\ }) | endif
endif

