""
" An experimental completion framework
"

if get(s:,'init','0')
	finish
endif
let s:init = 1
let s:already_setup = 0

inoremap <silent> <expr> <Plug>(cm_inject_snippet) <SID>check_and_inject_snippet()

" use silent mapping that doesn't slower the terminal ui
" Note: `:help complete()` says:
" > You need to use a mapping with CTRL-R = |i_CTRL-R|.  It does not work
" > after CTRL-O or with an expression mapping.
" 
" They all work. use g:cm_completekeys to decide which one to use.
inoremap <silent> <Plug>(cm_complete) <C-r>=cm#_complete()<CR>
inoremap <silent> <Plug>(cm_completefunc) <c-x><c-u>
inoremap <silent> <Plug>(cm_omnifunc) <c-x><c-o>

" Show the popup menu, reguardless of the matching of cm_refresh_pattern
inoremap <silent> <expr> <Plug>(cm_force_refresh) (cm#menu_selected()?"\<c-y>\<c-r>=cm#_force_refresh()\<CR>":"\<c-r>=cm#_force_refresh()\<CR>")


let s:rpcnotify = 'rpcnotify'
let s:jobstart = 'jobstart'
let s:jobstop = 'jobstop'
let g:_cm_servername = v:servername
if has('nvim')==0
	let s:rpcnotify = 'neovim_rpc#rpcnotify'
	let s:jobstart = 'neovim_rpc#jobstart'
	let s:jobstop = 'neovim_rpc#jobstop'
endif


" do nothing. place it here only to avoid the message 'No matching autocommands'
autocmd User CmSetup silent 

func! cm#enable_for_buffer(...)

	if has('nvim')==0
		let g:_cm_servername = neovim_rpc#serveraddr()
	endif

	if s:already_setup == 0
		doautocmd User CmSetup
		let s:already_setup = 1
	endif

	" remove to avoid conflict: #34
	" NCM uses cursorpos to detect changes currently, There's no need to keep
	" this mapping.
	"
	" " Notice: Workaround for neovim's bug. When the popup menu is visible, and
	" " no item is selected, an enter key will close the popup menu, change and
	" " move nothong, and then trigger TextChangedI and CursorMovedI
	" " https://github.com/neovim/neovim/issues/5997
	" inoremap <expr> <buffer> <CR> (pumvisible() ? "\<c-y>\<cr>" : "\<CR>")

	let b:cm_enable = 1
	if len(a:000)
		let b:cm_enable = a:1
	endif

	" TODO this override the global options, any way to fix this?
	let &completeopt=g:cm_completeopt
	if g:cm_completekeys=="\<Plug>(cm_completefunc)"
		set completefunc=cm#_completefunc
	endif
	if g:cm_completekeys=="\<Plug>(cm_omnifunc)"
		set omnifunc=cm#_completefunc
	endif

	augroup cm
		autocmd! * <buffer>
		autocmd InsertEnter <buffer> call s:notify_core_channel('cm_insert_enter') | call s:on_insert_enter()
		autocmd InsertLeave <buffer> call s:change_tick_stop()
		autocmd BufEnter    <buffer> let &completeopt=g:cm_completeopt
		" working together with timer, the timer is for detecting changes
		" popup menu is visible. TextChangedI will not be triggered when popup
		" menu is visible, but TextChangedI is more efficient and faster than
		" timer when popup menu is not visible.
		autocmd TextChangedI <buffer> call s:check_changes()
	augroup END

    call s:start_core_channel()

    call s:check_rtp()
endfunc

func! cm#disable_for_buffer()
	let b:cm_enable = 0
	augroup cm
		autocmd! * <buffer>
	augroup END
	call s:change_tick_stop()
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
	if l:ret['filepath'] == ''
		" this is necessary here, otherwise empty filepath is somehow
		" converted to None in vim's python binding.
		let l:ret['filepath'] = ""
	endif
	let l:ret['typed'] = strpart(getline(l:ret['lnum']),0,l:ret['col']-1)
	return l:ret
endfunc

func! cm#context_changed(ctx)
	" return (b:changedtick!=a:ctx['changedtick']) || (getcurpos()!=a:ctx['curpos'])
	" Note: changedtick is triggered when `<c-x><c-u>` is pressed due to vim's
	" bug, use curpos as workaround
	return getcurpos()!=a:ctx['curpos']
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

	let l:name = a:info['name']

	" if registered before, ignore this call
	if has_key(g:_cm_sources,l:name)
		return
	endif

	if has_key(g:cm_sources_override,l:name)
		" override source default options
		call extend(a:info,g:cm_sources_override[l:name])
	endif

	let a:info['enable'] = get(a:info,'enable',g:cm_sources_enable)

    " the name cm_refresh_min_word_len is deprecated, it will be removed
    " in the future
    if has_key(a:info, 'cm_refresh_min_word_len')
        let a:info['cm_refresh_length'] = a:info['cm_refresh_min_word_len']
    endif

	if !has_key(a:info,'cm_refresh_length')
		if type(g:cm_refresh_length)==type(1)
			let a:info['cm_refresh_length'] = g:cm_refresh_length
		else
			" format: [ [ minimal priority, min length ], []]
			"
			" Configure by min priority level. Use the max priority setting
			" available
			let l:max = -1
			for l:e in g:cm_refresh_length
				if (a:info['priority'] >= l:e[0]) && (l:e[0] > l:max)
					let a:info['cm_refresh_length'] = l:e[1]
					let l:max = l:e[0]
				endif
			endfor
		endif
	endif

	" wether or not use the framework's standard sorting
	let a:info['sort'] = get(a:info,'sort',1)

	" similar to g:cm_auto_popup
	let a:info['auto_popup'] = get(a:info,'auto_popup',1)

	let a:info['early_cache'] = get(a:info,'early_cache', 0)

	let g:_cm_sources[l:name] = a:info

	call s:notify_core_channel('cm_start_channels',g:_cm_sources,cm#context())

endfunc

func! cm#disable_source(name)
	try
		let l:info = g:_cm_sources[a:name]
		let l:info['enable'] = 0
		call cm#_channel_cleanup(l:info)
	catch
		echom v:exception
	endtry
endfunc


"""
" @param source name of the completion source. 
" @param startcol `help complete()`
" @param matches `help complete()`
"
" @return 
"   0 cm accepted
"	1 context changed
func! cm#complete(src, context, startcol, matches, ...)

	let l:refresh = 0
	if len(a:000)
		let l:refresh = a:1
	endif

	" ignore the request if context has changed
	if  cm#context_changed(a:context)
		call s:notify_core_channel('cm_complete',g:_cm_sources,a:src,a:context,a:startcol,a:matches,l:refresh,1,cm#context())
		return 1
	endif

	call s:notify_core_channel('cm_complete',g:_cm_sources,a:src,a:context,a:startcol,a:matches,l:refresh,0,'')
	return 0

endfunc

" show message to user
func! cm#message(msgtype, msg)
    if toupper(a:msgtype) == 'ERROR'
        if mode() == 'i'
            " side effect
            set nosmd
        endif
        echoh WarningMsg | echom '[ERROR] ' . a:msg | echoh None 
        return
    endif
    echom '[' . toupper(a:msgtype) . '] ' . a:msg
endfunc

" internal functions and variables

let g:_cm_sources = {}
let s:leaving = 0
let s:change_timer = -1
let s:lasttick = []
let s:channel_jobid = -1
let g:_cm_channel_id = -1
let s:channel_started = 0
let g:_cm_start_py_path = globpath(&rtp,'pythonx/cm_start.py',1)
let s:snippets = []
let s:complete_start_timer = 0
let s:old_rtp = &rtp

" global lock for being compatible with other plugins:
" 1 - vim-multiple-cursors
let g:_cm_lock = 0

augroup cm
	autocmd!
	autocmd VimLeavePre * let s:leaving=1

    autocmd User MultipleCursorsPre  let g:_cm_lock = or(g:_cm_lock, 0x1)
    autocmd User MultipleCursorsPost let g:_cm_lock = and(g:_cm_lock, invert(0x1))
augroup END

func! s:check_scope(info)
	let l:scopes = get(a:info,'scopes',[])
	if empty(l:scopes)
		" This is a general completion source
		return 1
	endif
	" only check the root scope
	let l:cur_scope = &filetype
	for l:scope in l:scopes
		if l:scope == l:cur_scope
			return 1
		endif
	endfor
	return 0
endfunc

func! cm#_core_channel_started(id)
	let g:_cm_channel_id = a:id
	" start channels as soon as possible
	call s:notify_core_channel('cm_start_channels',g:_cm_sources,cm#context())
endfunc

func! cm#_channel_started(name,id)

	if !has_key(g:_cm_sources,a:name)
		return
	endif

	let l:channel = g:_cm_sources[a:name]['channel']
	let l:channel['id'] = a:id

	" register events
	execute 'augroup cm_channel_' . a:id
	for l:event in get(l:channel,'events',[])
		let l:exec =  'if get(b:,"cm_enable",0) | silent! call call(s:rpcnotify,[' . a:id . ', "cm_event", "'.l:event.'",cm#context()]) | endif'
		if type(l:event)==type('')
			execute 'au ' . l:event . ' * ' . l:exec
		elseif type(l:event)==type([])
			execute 'au ' . join(l:event,' ') .' ' .  l:exec
		endif
	endfor
	execute 'augroup END'

	" refresh for this channel
	call s:on_changed()

endfunc

func! cm#_channel_cleanup(info)

	if !has_key(a:info,'channel')
		return
	endif

	let l:channel = a:info['channel']

	if has_key(l:channel,'id')
		" clean event group
		execute 'augroup cm_channel_' . l:channel['id']
		execute 'autocmd!'
		execute 'augroup END'
		unlet l:channel['id']
	endif

	let l:channel['has_terminated'] = 1

endfunc

func! cm#_core_complete(context, startcol, matches, not_changed, snippets)

    if s:should_skip()
        return
    endif

	" ignore the request if context has changed
	if  cm#context_changed(a:context)
		return
	endif

	if a:not_changed && pumvisible()
		return
	endif

	" from core channel
	" something selected by user, do not refresh the menu
	if cm#menu_selected()
		return
	endif

	let s:context = a:context
	let s:startcol = a:startcol
	let l:padcmd = 'extend(v:val,{"abbr":printf("%".strdisplaywidth(v:val["padding"])."s%s","",v:val["abbr"])})'
	let s:matches = map(a:matches, l:padcmd)
	let s:snippets = a:snippets

	call feedkeys(g:cm_completekeys, 'i')

endfunc

func! cm#_completefunc(findstart,base)
	if a:findstart
		return s:startcol-1
	endif
	return {'refresh': 'always', 'words': s:matches }
endfunc

func! cm#_complete()
	call complete(s:startcol, s:matches)
	return ''
endfunc

func! cm#_force_refresh()
	" force=1
	call s:notify_core_channel('cm_refresh',g:_cm_sources,cm#context(),1)
	return ''
endfunc

" cm core channel functions
" {


function! s:on_core_channel_error(job_id, data, event)
	echoe join(a:data,"\n")
endfunction

func! s:start_core_channel(...)
	if s:channel_started
		return
	endif
	let s:channel_started = 1

	let g:_cm_py3 = get(g:,'python3_host_prog','')
    if g:_cm_py3 == '' && has('python3')
        " heavy weight
        " but better support for python detection
        python3 import sys
        let g:_cm_py3 = py3eval('sys.executable')
    endif
    if g:_cm_py3 == ''
        let g:_cm_py3 = 'python3'
    endif

	let s:channel_jobid = call(s:jobstart,[[g:_cm_py3, g:_cm_start_py_path, 'core', g:_cm_servername], {
			\ 'on_exit' : function('s:on_core_channel_exit'),
			\ 'on_stderr' : function('s:on_core_channel_error'),
			\ 'detach'  : 1,
			\ }])
endfunc

fun s:on_core_channel_exit(job_id, data, event)
	let s:channel_jobid = -1
	if s:leaving
		return
	endif
	echom 'nvim-completion-manager core channel terminated'
endf

fun s:notify_core_channel(event,...)
	" if s:channel_jobid==-1
	if g:_cm_channel_id==-1
		return -1
	endif
	" forward arguments
	call call(s:rpcnotify,[g:_cm_channel_id, a:event] + a:000 )
	return 0
endf
" }

func! s:changetick()
	" return [b:changedtick , getcurpos()]
	" Note: changedtick is triggered when `<c-x><c-u>` is pressed due to vim's
	" bug, use curpos as workaround
	return getcurpos()
endfunc

func! s:should_skip()
    return !get(b:,'cm_enable',0)  || &paste!=0 || g:_cm_lock || mode() != 'i'
endfunc

func! s:check_rtp()
    if s:old_rtp != &rtp
        let s:old_rtp = &rtp
        call s:notify_core_channel('cm_detect_modules')
    endif
endfunc

func! s:on_insert_enter()
    call s:check_rtp()

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
	let s:lasttick = []
	let s:change_timer = -1
endfunc


func! s:check_changes(...)

    if s:should_skip()
        return
    endif

	let l:tick = s:changetick()

	if l:tick!=s:lasttick
		let s:lasttick = l:tick

        if g:cm_complete_start_delay == 0
            call s:on_changed()
        else
            if s:complete_start_timer
                call timer_stop(s:complete_start_timer)
            endif
            let s:complete_start_timer = timer_start(g:cm_complete_start_delay, function('s:complete_start_timer_handler'), {'repeat': 1})
        endif
	endif

	call s:check_and_inject_snippet()
endfunc

func! s:complete_start_timer_handler(...)
    let s:complete_start_timer = 0
    call s:on_changed()
endfunc

func! s:check_and_inject_snippet()

	if empty(v:completed_item) || !has_key(v:completed_item,'info') || empty(v:completed_item.info) || has_key(v:completed_item,'snippet')
		return ''
	endif

	let l:last_line = split(v:completed_item.info,'\n')[-1]
	if l:last_line[0:len('snippet@')-1]!='snippet@'
		return ''
	endif

	let l:snippet_id = str2nr(l:last_line[len('snippet@'):])
	if l:snippet_id>=len(s:snippets) || l:snippet_id<0
		return ''
	endif

	" neosnippet recognize the snippet field of v:completed_item. Also useful
	" for checking. Kind of a hack.
	let v:completed_item.snippet = s:snippets[l:snippet_id]['snippet']
    let v:completed_item.snippet_word = s:snippets[l:snippet_id]['word']

    if v:completed_item.snippet == ''
        return ''
    endif

	if g:cm_completed_snippet_engine == 'ultisnips'
		if get(b:,'_cm_us_setup',0)==0
			" UltiSnips_Manager.add_buffer_filetypes('%s.snips.ncm' % vim.eval('&filetype'))
			let b:_cm_us_setup = 1
			let b:_cm_us_filetype = 'ncm'
			call UltiSnips#AddFiletypes(b:_cm_us_filetype)
			autocmd InsertLeave <buffer> exec g:_uspy 'UltiSnips_Manager._added_snippets_source._snippets["ncm"]._snippets = []'
		endif
		exec g:_uspy 'UltiSnips_Manager._added_snippets_source._snippets["ncm"]._snippets = []'
		" TODO cleanup when InsertLeave
		call UltiSnips#AddSnippetWithPriority(v:completed_item.snippet_word, v:completed_item.snippet, '', 'i', b:_cm_us_filetype, 1)
	elseif g:cm_completed_snippet_engine == 'snipmate'
		if !exists('s:completed_item')
			let s:completed_item = {}
			autocmd InsertLeave * let s:completed_item = {}
			" inject ncm's handler into snipmate
			let g:snipMateSources['ncm'] = funcref#Function('cm#_snipmate_snippets')
		endif
		let s:completed_item = v:completed_item
	endif

    return ''
endfunc

func! cm#_snipmate_snippets(scopes, trigger, result)
	if empty(s:completed_item)
		return
	endif
	let a:result[s:completed_item['snippet_word']] = {'default': [s:completed_item.snippet,0] }
endfunc

" on completion context changed
func! s:on_changed()

    if s:should_skip()
        return
    endif

	if g:cm_auto_popup==0
		return
	endif

	call s:notify_core_channel('cm_refresh',g:_cm_sources,cm#context(),0)
endfunc

func! cm#_auto_enable_check(...)
	if exists('b:cm_enable') && b:cm_enable!=2
		return
	endif
	if (&buftype=='' &&  line2byte(line("$") + 1)<g:cm_buffer_size_limit) 
		" 2 for auto enable
		call cm#enable_for_buffer(2)
	else
		call cm#disable_for_buffer()
	endif
endfunc


func! cm#_notify_sources_to_refresh(calls, channels, ctx)

	for l:channel in a:channels
		try
			call call(s:rpcnotify, [l:channel['id'], 'cm_refresh', g:_cm_sources[l:channel['name']], l:channel['context']])
		catch
			continue
		endtry
	endfor
	for l:call in a:calls
		let l:name = l:call['name']
		try
			let l:type = type(g:_cm_sources[l:name].cm_refresh)
			if l:type==2
				" funcref
				call g:_cm_sources[l:name].cm_refresh(g:_cm_sources[l:name],l:call['context'])
			elseif l:type==1
				"string
				call call(g:_cm_sources[l:name].cm_refresh,[g:_cm_sources[l:name],l:call['context']],g:_cm_sources[l:name])
			elseif l:type==4 && has_key(g:_cm_sources[l:name].cm_refresh,'omnifunc')
				" dict
				call s:cm_refresh_omni(g:_cm_sources[l:name],l:call['context'])
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
	" there's no scoping context in omnifunc, use cm#context to get the root
	" context
	call cm#complete(a:opt, cm#context(), l:startcol, l:matches)
endfunc

func! cm#menu_selected()
	" when the popup menu is visible, v:completed_item will be the
	" current_selected item
	" if v:completed_item is empty, no item is selected
	return pumvisible() && !empty(v:completed_item)
endfunc

