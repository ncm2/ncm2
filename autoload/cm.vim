""
" An experimental completion framework
"

if get(s:,'init','0')
	finish
endif
let s:init = 1

" chech this plugin is enabled
" get(b:,'cm_enable',0)

func! cm#enable_for_buffer()

	" TODO this override the global options, any way to fix this?
	set completeopt=menu,menuone,noinsert,noselect

	" Notice: Workaround for neovim's bug. When the popup menu is visible, and
	" no item is selected, an enter key will close the popup menu, change and
	" move nothong, and then trigger TextChangedI and CursorMovedI
	" https://github.com/neovim/neovim/issues/5997
	inoremap <expr> <buffer> <CR> ((pumvisible() && empty(v:completed_item)) ?"\<ESC>a\<CR>" : "\<CR>")

	let b:cm_enable = 1

	augroup cm
		autocmd! * <buffer>
		autocmd InsertEnter,InsertLeave <buffer> let s:dict_matches = {} | let s:complete_mode = 0 | let s:noclean = 0
		autocmd CompleteDone <buffer> if s:noclean==0 | let s:dict_matches = {} | endif | let s:complete_mode = 0 | let s:noclean = 0
	augroup end

endfunc

func! cm#disable_for_buffer()
	if get(b:,'cm_enable',0)
		iunmap <buffer> <CR>
	endif
	let b:cm_enable = 0
	augroup cm
		autocmd! * <buffer>
	augroup end
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
	return {'bufnr':bufnr('%'), 'curpos':getcurpos(), 'changedtick':b:changedtick}
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
" priority shoud be defined 1 to 9, here's recommended definition:
"	2 keyword from the otherfiles, from user's openning browsers, etc
" 	4 keyword from openning buffer
" 	5 keyword from current buffer
" 	6 file path
" 	7 snippet hint
" 	9 smart programming language aware completion
func! cm#register_source(info)

	" if registered before, ignore this call
	if has_key(s:sources,a:info['name'])
		return
	endif

	let s:sources[a:info['name']] = a:info

	for l:channel in get(a:info,'channels',[])
		if l:channel['type']=='python3'
			" find script path
			let l:py3 = get(g:,'python3_host_prog','python3')
			let l:path = globpath(&rtp,l:channel['path'])
			if empty(l:path)
				echom 'cannot find channel path: ' . l:channel['path']
				continue
			endif

			let l:opt = {'rpc':1, 'channel': l:channel}

			func l:opt.on_exit()
				unlet self['channel']['id']
				if s:leaving
					return
				endif
				echom self['channel']['path'] . ' ' . 'exit'
				unlet self['channel']
			endfunc

			" start channel
			let l:channel['id'] = jobstart([l:py3,l:path],l:opt)
		endif
	endfor
endfunc


func! cm#remove_source(name)
	try
		let l:info = s:sources[a:name]
		for l:channel in get(l:info,'channels',[])
			try
				if has_key(l:channel,'id')
					jobstop(l:channel.id)
				endif
			catch
				continue
			endtry
		endfor
		unlet l:info
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
func! cm#complete(src, context, startcol, matches)

	if type(a:src)==1
		" string
		let l:name = a:src
	else
		" dict
		let l:name = a:src['name']
	endif

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
	let s:dict_matches[l:name] = {'startcol':a:startcol, 'matches':a:matches}

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
let s:leaving = 0

augroup cm
	autocmd!
	autocmd VimLeavePre * let s:leaving=1
	autocmd User PossibleTextChangedI call <sid>on_changed()
augroup end

" on completion context changed
func! s:on_changed()

	if get(b:,'cm_enable',0) == 0
		return
	endif

	let l:ctx = cm#context()
	for l:source in keys(s:sources)
		let l:info = s:sources[l:source]
		try
			if has_key(s:dict_matches,l:info['name']) && (get(l:info,'refresh',0)==0)
				" no need to refresh candidate, to reduce calculation
				continue
			endif
			if has_key(l:info,'on_changed')
				call l:info.on_changed(l:ctx)
			endif

			" notify channels
			for l:channel in get(l:info,'channels',[])
				if has_key(l:channel,'id')
					call rpcnotify(l:channel['id'], 'cm_on_changed', l:info, l:ctx)
				endif
			endfor

		catch
			echom 'error on completion source: ' . l:source . ' ' . v:exception
			continue
		endtry
	endfor

	" TODO
	" detect popup item selected event then notify sources
	
	" TODO
	" detect real complete done event then notify sources

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

