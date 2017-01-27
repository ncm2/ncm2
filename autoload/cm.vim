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

	" Notice: Workaround for neovim's bug. When the popup menu is visible, and
	" no item is selected, an enter key will close the popup menu, change and
	" move nothong, and then trigger TextChangedI and CursorMovedI
	" https://github.com/neovim/neovim/issues/5997
	inoremap <expr> <buffer> <CR> ((pumvisible() && empty(v:completed_item)) ?"\<ESC>a\<CR>" : "\<CR>")

	let b:cm_enable = 1

	let s:saved_completeopt = &completeopt
	" TODO this override the global options, any way to fix this?
	set completeopt=menu,menuone,noinsert,noselect

	augroup cm
		autocmd! * <buffer>
		autocmd InsertEnter <buffer> call s:notify_core_channel('cm_insert_enter') | let s:dict_matches = {}
		autocmd InsertLeave <buffer> call s:notify_core_channel('cm_insert_leave') | let s:dict_matches = {}
		autocmd InsertEnter <buffer> call s:change_tick_start()
		autocmd InsertLeave <buffer> call s:change_tick_stop()
		" save and restore completeopt
		autocmd BufEnter    <buffer> let s:saved_completeopt = &completeopt | set completeopt=menu,menuone,noinsert,noselect
		autocmd BufLeave    <buffer> let &completeopt = s:saved_completeopt
	augroup end

endfunc

func! cm#disable_for_buffer()
	if get(b:,'cm_enable',0)
		iunmap <buffer> <CR>
	endif
	let b:cm_enable = 0
	" restore completeopt
	let &completeopt = s:saved_completeopt
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
	let l:ret = {'bufnr':bufnr('%'), 'curpos':getcurpos(), 'changedtick':b:changedtick}
	let l:ret['lnum'] = l:ret['curpos'][1]
	let l:ret['col'] = l:ret['curpos'][2]
	let l:ret['typed'] = strpart(getline(l:ret['lnum']),0,l:ret['col']-1)
	return l:ret
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

				" delete event group
				execute 'augroup! cm_channel_' . self['channel']['id']

				unlet self['channel']['id']
				if s:leaving
					return
				endif
				echom self['channel']['path'] . ' ' . 'exit'
				unlet self['channel']
			endfunc

			" start channel
			let l:channel['id'] = jobstart([l:py3,s:core_py_path,'channel',l:path],l:opt)

			" events
			execute 'augroup cm_channel_' . l:channel['id']
			for l:event in get(l:channel,'events',[])
				let l:exec =  'if get(b:,"cm_enable",0) | call rpcnotify(' . l:channel['id'] . ', "cm_event", "'.l:event.'",cm#context()) | endif'
				if type(l:event)==type('')
					execute 'au ' . l:event . ' * ' . l:exec
				elseif type(l:event)==type([])
					execute 'au ' . join(l:event,' ') .' ' .  l:exec
				endif
			endfor
			execute 'augroup end'

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
"   3 this source has not been registered yet
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
	if  (a:context!=cm#context()) || (mode()!='i')
		return 1
	endif

	if !has_key(s:sources,l:name)
		return 3
	endif

	call s:notify_core_channel('cm_complete',s:sources,l:name,a:context,a:startcol,a:matches)

endfunc

" Note: internal function
func! cm#core_complete(context, startcol, matches, allmatches)

	if get(b:,'cm_enable',0) == 0
		return 2
	endif

	let s:dict_matches = a:allmatches

	" ignore the request if context has changed
	if  (a:context!=cm#context()) || (mode()!='i')
		return 1
	endif

	" from core channel
	" something selected by user, do not refresh the menu
	if s:menu_selected()
		return 0
	endif

	call complete(a:startcol, a:matches)

	return 0
endfunc

" internal functions and variables

let s:sources = {}
let s:leaving = 0
let s:change_timer = -1
let s:lasttick = ''
let s:channel_id = -1
let s:dir = expand('<sfile>:p:h')
let s:core_py_path = s:dir . '/cm.py'

augroup cm
	autocmd!
	autocmd VimLeavePre * let s:leaving=1
	" autocmd User PossibleTextChangedI call <sid>on_changed()
augroup end

" cm core channel functions
" {
func! s:start_core_channel()
	let l:py3 = get(g:,'python3_host_prog','python3')
	let s:channel_id = jobstart([l:py3,s:core_py_path,'core'],{'rpc':1,
			\ 'on_exit' : function('s:on_core_channel_exit'),
			\ })

			" \ 'cwd'     : s:dir,
endfunc

fun s:on_core_channel_exit()
	let s:channel_id = -1
	if s:leaving
		return
	endif
	echom 'cm-core channel exit'
endf

fun s:notify_core_channel(event,...)
	if s:channel_id==-1
		return -1
	endif
	" forward arguments
	call call('rpcnotify',[s:channel_id, a:event] + a:000 )
	return 0
endf
" }

func! s:changetick()
	return [b:changedtick , getcurpos()]
endfunc

func! s:change_tick_start()
	if s:change_timer!=-1
		return
	endif
	let s:lasttick = s:changetick()
	" check changes every 30ms, which is 0.03s, it should be fast enough
	let s:change_timer = timer_start(30,function('s:check_changes'),{'repeat':-1})
	call s:on_changed()
endfunc

func! s:change_tick_stop()
	if s:change_timer==-1
		return
	endif
	call timer_stop(s:change_timer)
	let s:lasttick = ''
	let s:change_timer = -1
endfunc


func! s:check_changes(timer)
	let l:tick = s:changetick()
	if l:tick!=s:lasttick
		let s:lasttick = l:tick
		if mode()=='i' && (&paste==0)
			" only in insert non paste mode
			call s:on_changed()
		endif
	endif
endfunc

" on completion context changed
func! s:on_changed()

	if get(b:,'cm_enable',0) == 0
		return
	endif

	let l:ctx = cm#context()

	call s:notify_core_channel('cm_refresh',s:sources,l:ctx)

	" TODO
	" detect popup item selected event then notify sources

endfunc

func! cm#notify_sources_to_refresh(calls, channels, ctx)
	for l:name in a:calls
		try
			if type(s:sources[l:name].cm_refresh)==2
				" funcref
				call s:sources[l:name].cm_refresh(a:ctx)
			elseif type(s:sources[l:name].cm_refresh)==1
				"string
				call call(s:sources[l:name].cm_refresh,[a:ctx],s:sources[l:name])
			endif
		catch
			continue
		endtry
	endfor
	for l:channel in a:channels
		try
			call rpcnotify(l:channel['id'], 'cm_refresh', s:sources[l:channel['name']], a:ctx)
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

if v:vim_did_enter
	call s:start_core_channel()
else
	au VimEnter * call s:start_core_channel()
endif

