""
" An experimental completion framework
"


" chech this plugin is enabled
" get(b:,'cm_enable',0)

func! cm#enable_for_buffer()

	" TODO this override the global options, any way to fix this?
	set completeopt=menu,menuone,noinsert,noselect

	" Notice: Workaround for neovim's bug. When the popup menu is visible, and
	" no item is selected, an enter key will close the popup menu, change and
	" move nothong, and then trigger TextChangedI and CursorMovedI
	" https://github.com/neovim/neovim/issues/5997
	inoremap <expr> <buffer> <CR> ((pumvisible() && empty(v:completed_item)) ?"\<CR>\<CR>" : "\<CR>")

	let b:cm_enable = 1

endfunc

"""
" before calculating the completion candidates, use this function to get the
" current execution context
"
" If the context changed during calculation, the call to
" cm#complete(source,context, startcol, matches) will be ignored
"
" you could use `l:context != cm#context()` to determine wether the context
" has changed by yourself
func! cm#context()
	return [bufnr('%'), getcurpos(), b:changedtick]
endfunc


"""
" Use this function to register your completion source and detect the
" existance of this plugin:
"
" try
"   call cm#register_source(info)
" catch
"   " this plugin is not installed yet
"   finish
" endtry
"
" @param info  
"	{'name':'cm-buffer-keyword', 'priority': 5, 'abbreviation': 'bword'}
"
" priority shoud be defined 1 to 9:
"	3 keyword from the otherfiles, from user's openning browsers, etc
" 	4 keyword from openning buffer
" 	5 keyword from current buffer
" 	6 snippet hint
" 	7 smart programming language aware completion
func! cm#register_source(info)
	let s:sources[a:info['name']] = a:info
endfunc

func! cm#remove_source(name)
	try
		unlet s:sources[a:name]
	catch
		return
	endtry
endfunc


"""
" @param source name of the completion source. 
" @param startcol `help complete()`
" @param matches `help complete()`
"
" @return 
"   0 cm accepted
"	1 ignored for context change
"   2 async completion has been disabled
func! cm#complete(source_name, context, startcol, matches)

	if get(b:,'cm_enable',0) == 0
		return 2
	endif

	" ignore the request if context has changed
	if  a:context != cm#context()
		return 1
	endif

	if mode()!='i'
		return 1
	endif

	if empty(a:matches)
		return 0
	endif

	" update the local store
	let s:dict_matches[a:source_name] = {'startcol':a:startcol, 'matches':a:matches}

	" menu selected
	if s:menu_selected()
		return 0
	endif

	" if no item is selected, refresh the popup menu
	call s:refresh_popup()

endfunc


" internal functions and variables

let s:sources = {}
let s:dict_matches = {}
let s:complete_mode = 0
let s:noclean = 0 " do not clean d:dict_matches for next CompleteDone event

augroup cm
	autocmd!
	autocmd InsertEnter,InsertLeave * let s:dict_matches = {} | let s:complete_mode = 0 | let s:noclean = 0
	autocmd CompleteDone * if s:noclean==0 | let s:dict_matches = {} | endif | let s:complete_mode = 0 | let s:noclean = 0
	autocmd User PossibleTextChangedI call <sid>on_changed()
augroup end

" on completion context changed
func! s:on_changed()
	let l:ctx = cm#context()
	for l:source in keys(s:sources)
		let l:info = s:sources[l:source]
		try
			if has_key(s:dict_matches,l:info['name']) && (get(l:info,'refresh',0)==0)
				" no need to refresh candidate, to reduce calculation
				continue
			endif
			call l:info['on_changed'](l:ctx)
		catch
			continue
		endtry
	endfor
endfunc

func! s:menu_selected()
	" when the popup menu is visible, v:completed_item will be the
	" current_selected item
	" if v:completed_item is empty, no item is selected
	return pumvisible() && !empty(v:completed_item)
endfunc

func! s:refresh_popup()

	if empty(s:dict_matches)
		return
	endif

	let l:sources = sort(keys(s:dict_matches),function('s:compare_source_priority'))

	let l:startcol = s:dict_matches[l:sources[0]]['startcol']

	for l:source in l:sources
		let l:tmp = s:dict_matches[l:source]['startcol']
		if l:tmp < l:startcol
			let l:startcol = l:tmp
		endif
	endfor

	let l:matches = []

	let l:col = col('.')
	let l:line = getline('.')
	for l:source in l:sources

		try

			let l:s = s:dict_matches[l:source]['startcol']
			let l:m = s:dict_matches[l:source]['matches']

			let l:prefix = strpart(l:line, l:startcol-1, l:s-l:startcol)

			for l:e in l:m
				try
					if type(l:e)==1
						" string
						let l:add = {'word': l:prefix . l:e}
					else
						let l:add = copy(l:e)
						let l:add['word'] = l:prefix . l:add['word']
					endif
					let l:add['dup'] = 1
					let l:add['menu'] = get(s:sources[l:source],'abbreviation','unknown')
					let l:matches = add(l:matches, l:add)
				catch
					continue
				endtry
			endfor
		catch
			continue
		endtry

	endfor

	if s:complete_mode
		" if in complete mode, call complete will trigger a CompleteDone event
		let s:noclean = 1
	endif
	call complete(l:startcol, l:matches)
	" hacky
	let s:complete_mode = 1

endfunc

func! s:compare_source_priority(source1,source2)
	let l:p1 = get(get(s:sources,a:source1,{}),'priority',0)
	let l:p2 = get(get(s:sources,a:source2,{}),'priority',0)
	if l:p1 > l:p2
		return -1
	endif
	return l:p1!=l:p2
endfunc

