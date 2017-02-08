""
" An experimental completion framework
"

if get(s:,'init','0')
	finish
endif
let s:init = 1
let s:already_setup = 0

" use silent mapping that doesn't slower the terminal ui
inoremap <silent> <Plug>(cm_complete) <C-r>=cm#_complete()<CR>
" <nop> for preventing context changing
nnoremap <silent> <Plug>(cm_complete) <nop>
onoremap <silent> <Plug>(cm_complete) <nop>
" visual and select
vnoremap <silent> <Plug>(cm_complete) <nop>
snoremap <silent> <Plug>(cm_complete) <nop>
cnoremap <silent> <Plug>(cm_complete) <nop>
tnoremap <silent> <Plug>(cm_complete) <nop>

" options

" wait for a while before popping up, in milliseconds, this would reduce the
" popup menu flashes when multiple sources are updating the popup menu in a
" short interval, use a interval which is long enough for computer and short
" enough for human
let g:cm#complete_delay = get(g:,'complete_delay',50)

" chech this plugin is enabled
" get(b:,'cm_enable',0)

" do nothing, place it here only to avoid the message 'No matching autocommands'
autocmd User CmSetup silent 

func! cm#enable_for_buffer()

	if s:already_setup == 0
		call s:register_builtin_sources()
		doautocmd User CmSetup
		let s:already_setup = 1
	endif

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
		autocmd InsertEnter <buffer> call s:notify_core_channel('cm_insert_enter')
		autocmd InsertLeave <buffer> call s:notify_core_channel('cm_insert_leave')
		autocmd InsertEnter <buffer> call s:change_tick_start()
		autocmd InsertLeave <buffer> call s:change_tick_stop()
		autocmd FileType,BufWinEnter <buffer> call s:check_and_start_all_channels()
		" save and restore completeopt
		autocmd BufWinEnter    <buffer> let s:saved_completeopt = &completeopt | set completeopt=menu,menuone,noinsert,noselect
		autocmd BufWinLeave    <buffer> let &completeopt = s:saved_completeopt
	augroup END

	call s:start_core_channel()
	call s:check_and_start_all_channels()

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
	augroup END
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
	let l:ret['filetype'] = &filetype
	let l:ret['filepath'] = expand('%:p')
	let l:ret['typed'] = strpart(getline(l:ret['lnum']),0,l:ret['col']-1)
	return l:ret
endfunc

func! cm#context_changed(ctx)
	return (b:changedtick!=a:ctx['changedtick']) || (getcurpos()!=a:ctx['curpos'])
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
" 	8 language specific keyword, but not smart
" 	9 smart programming language aware completion
func! cm#register_source(info)

	" if registered before, ignore this call
	if has_key(s:sources,a:info['name'])
		return
	endif

	let s:sources[a:info['name']] = a:info

	" check and start channels
	if get(b:,'cm_enable',0) == 0
		return
	endif

	call s:check_and_start_channels(a:info)

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
	if  cm#context_changed(a:context) || (mode()!='i')
		return 1
	endif

	if !has_key(s:sources,l:name)
		return 3
	endif

	call s:notify_core_channel('cm_complete',s:sources,l:name,a:context,a:startcol,a:matches)

endfunc

" internal functions and variables

let s:sources = {}
let s:leaving = 0
let s:change_timer = -1
let s:lasttick = ''
let s:channel_id = -1
let s:channel_started = 0
let s:dir = expand('<sfile>:p:h')
let s:core_py_path = s:dir . '/cm_core.py'
" let s:complete_timer
let s:complete_timer_ctx = {}

augroup cm
	autocmd!
	autocmd VimLeavePre * let s:leaving=1
	" autocmd User PossibleTextChangedI call <sid>on_changed()
augroup END

func! s:check_and_start_all_channels()
	for l:name in keys(s:sources)
		call s:check_and_start_channels(s:sources[l:name])
	endfor
endfunc

func! s:check_scope(info)
	" check scopes
	let l:scopes = get(a:info,'scopes',['*'])
	let l:cur_scopes = [&filetype]
	for l:scope in l:scopes
		if l:scope=='*'
			" match any scope
			return 1
		endif
		for l:cur in l:cur_scopes
			if l:scope == l:cur
				return 1
			endif
		endfor
	endfor
	return 0
endfunc

" check and start channels
func! s:check_and_start_channels(info)
	if s:check_scope(a:info)==0
		return
	endif
	call cm#_start_channels(a:info)
endfunc

" called from cm_core.py
func! cm#_start_channels(info)
	let l:info = a:info
	if type(a:info)==type("")
		" parameter is a name
		let l:info = s:sources[a:info]
	endif
	for l:channel in get(l:info,'channels',[])

		if l:channel['type']=='python3'

			if get(l:channel, 'id',-1)!=-1
				" channel already started
				continue
			endif

			" find script path
			let l:py3 = get(g:,'python3_host_prog','python3')
			let l:path = globpath(&rtp,l:channel['path'],1)
			if empty(l:path)
				echom 'cannot find channel path: ' . l:channel['path']
				continue
			endif

			let l:opt = {'rpc':1, 'channel': l:channel}
			let l:opt['detach'] = get(l:channel,'detach',0)

			func l:opt.on_exit(job_id, data, event)

				" delete event group
				execute 'augroup cm_channel_' . self['channel']['id']
				execute 'autocmd!'
				execute 'augroup END'

				unlet self['channel']['id']
				" mark it
				let self['channel']['has_terminated'] = 1
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
			execute 'augroup END'

		endif
	endfor
	return l:info
endfunc

func! cm#_core_complete(context, startcol, matches)

	if get(b:,'cm_enable',0) == 0
		return
	endif

	" ignore the request if context has changed
	if  cm#context_changed(a:context)
		return
	endif

	" from core channel
	" something selected by user, do not refresh the menu
	if s:menu_selected()
		return
	endif

	let s:context = a:context
	let s:startcol = a:startcol
	let s:matches = a:matches

	" Note: `:help complete()` says:
	" > You need to use a mapping with CTRL-R = |i_CTRL-R|.  It does not work
	" > after CTRL-O or with an expression mapping.
	call feedkeys("\<Plug>(cm_complete)")

endfunc

func! cm#_complete()

	" ignore the request if context has changed
	if  cm#context_changed(s:context)
		return ''
	endif

	" from core channel
	" something selected by user, do not refresh the menu
	if s:menu_selected()
		return ''
	endif

	call complete(s:startcol, s:matches)
	return ''
endfunc

" cm core channel functions
" {
func! s:start_core_channel()
	if s:channel_started
		return
	endif
	let l:py3 = get(g:,'python3_host_prog','python3')
	let s:channel_id = jobstart([l:py3,s:core_py_path,'core'],{'rpc':1,
			\ 'on_exit' : function('s:on_core_channel_exit'),
			\ 'detach'  : 1,
			\ })

	let s:channel_started = 1
endfunc

fun s:on_core_channel_exit(job_id, data, event)
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

	if exists('s:complete_timer')
		call timer_stop(s:complete_timer)
		unlet s:complete_timer
	endif

	let l:ctx = cm#context()

	call s:notify_core_channel('cm_refresh',s:sources,l:ctx)

	" TODO
	" detect popup item selected event then notify sources

endfunc

func! cm#_notify_sources_to_refresh(calls, channels, ctx)

	if exists('s:complete_timer')
		call timer_stop(s:complete_timer)
		unlet s:complete_timer
	endif
	let s:complete_timer = timer_start(g:cm#complete_delay,function('s:complete_timeout'))
	let s:complete_timer_ctx = a:ctx

	for l:channel in a:channels
		try
			call rpcnotify(l:channel['id'], 'cm_refresh', s:sources[l:channel['name']], l:channel['context'])
		catch
			continue
		endtry
	endfor
	for l:call in a:calls
		let l:name = l:call['name']
		try
			let l:type = type(s:sources[l:name].cm_refresh)
			if l:type==2
				" funcref
				call s:sources[l:name].cm_refresh(s:sources[l:name],l:call['context'])
			elseif l:type==1
				"string
				call call(s:sources[l:name].cm_refresh,[s:sources[l:name],l:call['context']],s:sources[l:name])
			elseif l:type==4 && has_key(s:sources[l:name].cm_refresh,'omnifunc')
				" dict
				call s:cm_refresh_omni(s:sources[l:name],l:call['context'])
			endif
		catch
			echom "cm completion source " . l:name . " exception caught: " . v:exception
			continue
		endtry
	endfor
endfunc


" omni completion wrapper for cm_refresh
func! s:cm_refresh_omni(opt,ctx)
	" omni function's startcol is zero based, convert it to one based
	let l:startcol = call(a:opt['cm_refresh']['omnifunc'],[1,'']) + 1
	let l:typed = a:ctx['typed']
	let l:base = l:typed[l:startcol-1:]
	let l:matches = call(a:opt['cm_refresh']['omnifunc'],[0, l:base])
	if type(l:matches)!=type([])
		return
	endif
	" echom a:opt['name'] . ", col: " . l:startcol . " matches: " . json_encode(l:matches)
	call cm#complete(a:opt, a:ctx, l:startcol, l:matches)
endfunc

func! s:complete_timeout(timer)
	" finished, clean variable
	unlet s:complete_timer
	if cm#context_changed(s:complete_timer_ctx)
		return
	endif
	call s:notify_core_channel('cm_complete_timeout',s:sources,s:complete_timer_ctx)
endfunc

func! s:menu_selected()
	" when the popup menu is visible, v:completed_item will be the
	" current_selected item
	" if v:completed_item is empty, no item is selected
	return pumvisible() && !empty(v:completed_item)
endfunc

func! s:register_builtin_sources()

	call cm#register_source({'name' : 'cm-ultisnips',
		\ 'priority': 7, 
		\ 'abbreviation': 'Snips',
		\ 'cm_refresh': 'cm#sources#ultisnips#cm_refresh',
		\ })

	" css
	" the omnifunc pattern is PCRE
	call cm#register_source({'name' : 'cm-css',
		\ 'priority': 9, 
		\ 'scopes': ['css'],
		\ 'abbreviation': 'css',
		\ 'cm_refresh': {'omnifunc': 'csscomplete#CompleteCSS', 'patterns':['\w{2,}$',':\s+\w*$'] },
		\ })


	" Note: the channels field is required as an array, on most cases only one
	" channel will would be enough. While there may be cases in which you need
	" another thread to do the indexing, caching work, it's easier to use another
	" channel instead of controlling threading on your own.

	" keyword
	call cm#register_source({
			\ 'name' : 'cm-bufkeyword',
			\ 'priority': 5, 
			\ 'abbreviation': 'Key',
			\ 'channels': [
			\   {
			\		'type': 'python3',
			\		'path': 'autoload/cm/sources/cm_bufkeyword.py',
			\		'events':['CursorHold','CursorHoldI','BufEnter','BufWritePost','TextChangedI'],
			\		'detach':1,
			\	}
			\ ],
			\ })

	" tags
	call cm#register_source({
			\ 'name' : 'cm-tags',
			\ 'priority': 6, 
			\ 'abbreviation': 'Tag',
			\ 'channels': [
			\   {
			\		'type': 'python3',
			\		'path': 'autoload/cm/sources/cm_tags.py',
			\		'events':['WinEnter'],
			\		'detach':1,
			\	}
			\ ],
			\ })


	" tmux
	call cm#register_source({
			\ 'name' : 'cm-tmux',
			\ 'priority': 4, 
			\ 'abbreviation': 'Tmux',
			\ 'channels': [
			\   {
			\		'type': 'python3',
			\		'path': 'autoload/cm/sources/cm_tmux.py',
			\		'events':['CursorHold','CursorHoldI','FocusGained','BufEnter'],
			\		'detach':1,
			\	}
			\ ],
			\ })


	" filepath
	call cm#register_source({
			\ 'name' : 'cm-filepath',
			\ 'priority': 6, 
			\ 'abbreviation': 'path',
			\ 'channels': [
			\   {
			\		'type': 'python3',
			\		'path': 'autoload/cm/sources/cm_filepath.py',
			\		'detach': 1,
			\   }
			\ ],
			\ })

	" jedi
	" refresh 1 for call signatures
	" detach 0, jedi enters infinite loops sometime, don't know why.
	call cm#register_source({
			\ 'name' : 'cm-jedi',
			\ 'priority': 9, 
			\ 'abbreviation': 'Py',
			\ 'scopes': ['python'],
			\ 'refresh': 1, 
			\ 'channels': [
			\   {
			\		'type': 'python3',
			\		'path': 'autoload/cm/sources/cm_jedi.py',
			\		'events': ['InsertLeave'],
			\		'detach': 0,
			\   }
			\ ],
			\ })

	" gocode
	call cm#register_source({
			\ 'name' : 'cm-gocode',
			\ 'priority': 9, 
			\ 'abbreviation': 'Go',
			\ 'scopes': ['go'],
			\ 'channels': [
			\   {
			\		'type': 'python3',
			\		'path': 'autoload/cm/sources/cm_gocode.py',
			\		'detach': 1,
			\   }
			\ ],
			\ })

	" tern
	call cm#register_source({
			\ 'name' : 'cm-tern',
			\ 'priority': 9, 
			\ 'abbreviation': 'Js',
			\ 'scopes': ['javascript','javascript.jsx'],
			\ 'channels': [
			\   {
			\		'type': 'python3',
			\		'path': 'autoload/cm/sources/cm_tern.py',
			\		'detach': 1,
			\   }
			\ ],
			\ })

endfunc

