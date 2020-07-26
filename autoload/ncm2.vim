if get(g:,'ncm2_loaded','0')
    finish
endif
let g:ncm2_loaded = 1

func! s:opt(name, default)
    let val = get(g:, a:name, a:default)
    let cmd = 'let g:' . a:name . '= l:val'
    execute cmd
endfunc

call s:opt('ncm2#auto_popup', 1)
call s:opt('ncm2#complete_delay', 0)
call s:opt('ncm2#popup_delay', 60)
call s:opt('ncm2#complete_length', [[1,3],[7,2]])
call s:opt('ncm2#manual_complete_length', g:ncm2#complete_length)
call s:opt('ncm2#matcher', 'abbrfuzzy')
call s:opt('ncm2#sorter', 'abbrfuzzy')
call s:opt('ncm2#filter', [])
call s:opt('ncm2#popup_limit', -1)
call s:opt('ncm2#total_popup_limit', -1)
call s:opt('ncm2#auto_extra_text_edits', 1)

inoremap <silent> <Plug>(ncm2_auto_trigger)      <c-r>=ncm2#auto_trigger()<cr>
inoremap <silent> <Plug>(ncm2_skip_auto_trigger) <c-r>=ncm2#skip_auto_trigger()<cr>
inoremap <silent> <Plug>(ncm2_manual_trigger)    <c-r>=ncm2#manual_trigger()<cr>

inoremap <silent> <expr> <Plug>(ncm2_c_e) (pumvisible() ? "\<c-e>" : '')

let s:core = yarp#py3('ncm2_core')
let s:core.on_load = 'ncm2#_core_started'
let s:sources = {}
let s:sources_override = {}
let s:complete_timer = 0
let s:popup_timer = 0
let s:popup_timer_args = []
let s:popup_timer_tick = []
let s:lock = {}
let s:startbcol = 1
let s:lnum = 0
let s:matches = []
let s:subscope_detectors = {}
let s:auto_trigger_tick = []
let s:skip_context_id = 0
let s:context_id = 0
let s:completion_notified = {}
let s:coredata_hooks = {}
let s:popup_open = 0
let s:popup_closed_by_user = 0
let s:popup_close_tick = []
let s:popup_close_check_state = 0

augroup ncm2_hooks
    au!
    au User Ncm2EnableForBuffer call s:on_warmup()
    au FileType * call s:try_rnotify('load_plugin', &rtp)
augroup END

func! ncm2#enable_for_buffer()
    if get(b:, 'ncm2_enable', 0)
        return
    endif
    let b:ncm2_enable = 1

    augroup ncm2_buf_hooks
        au! * <buffer>
        au InsertEnter,InsertLeave <buffer> call s:on_insert_enter()
        au BufEnter <buffer> call s:on_warmup()
        if exists('##TextChangedP')
            au TextChangedI,TextChangedP <buffer> call ncm2#imode_task('ncm2#auto_trigger')
            au InsertEnter <buffer> call ncm2#imode_task('ncm2#auto_trigger')
        else
            au TextChangedI <buffer> call ncm2#imode_task('ncm2#auto_trigger')
            au InsertCharPre,InsertEnter <buffer> call ncm2#imode_task('ncm2#auto_trigger')
        endif
        au CompleteDone <buffer> call s:on_complete_done()
    augroup END

    doau <nomodeline> User Ncm2EnableForBuffer
endfunc

func! ncm2#disable_for_buffer()
    let b:ncm2_enable = 0
    augroup ncm2_buf_hooks
        au! * <buffer>
    augroup END
endfunc

func! s:on_complete_done()
    call ncm2#imode_task('ncm2#_check_popup_close')

    let item = ncm2#completed_item()
    if empty(item)
        return
    endif

    call ncm2#_check_popup_close()

    let ctx = s:context()
    let name = item.user_data.source
    if !has_key(s:sources, name)
        call ncm2#_do_extra_text_edits(ctx, item)
    endif
    let sr = s:sources[name]
    if has_key(sr, 'on_complete_resolve')
        let ctx.on_complete_resolved = 'ncm2#_do_extra_text_edits'
        call call(sr.on_complete_resolve, [ctx, item])
    else
        call ncm2#_do_extra_text_edits(ctx, item)
    endif
endfunc

func! ncm2#_do_extra_text_edits(ctx, item)
    if a:ctx.tick != ncm2#context_tick()
        return
    endif

    " if g:ncm2#auto_extra_text_edits
    " endif

    " TODO expand snippet, but how to transfer the resolved item to the expand
    " key ?
    "
    " call ncm2#confirm_snippet_expand ???
endfunc

func! s:on_insert_enter()
    call s:cache_matches_cleanup()
    let s:auto_trigger_tick  = []
    let s:popup_close_tick = []
    call s:try_rnotify('cache_cleanup')
endfunc

func! s:cache_matches_cleanup()
    let s:matches = []
    let s:lnum = 0
    let s:startbcol = 1
endfunc

func! ncm2#context_tick()
    " FIXME b:changedtick ticks when <c-y> is typed.  curswant of
    " getcurpos() also ticks sometimes after <c-y> is typed. Use cursor
    " position to filter the requests.
    return getcurpos()[0:2]
endfunc

func! s:context()
    let s:context_id += 1
    let pos = getcurpos()
    let bcol = pos[2]
    let typed = strpart(getline('.'), 0, bcol-1)
    let ctx = {   'bufnr': bufnr('%'),
                \ 'curpos': pos,
                \ 'changedtick': b:changedtick,
                \ 'lnum': pos[1],
                \ 'bcol': bcol,
                \ 'ccol': strchars(typed) + 1,
                \ 'filetype': &filetype,
                \ 'scope': &filetype,
                \ 'filepath': expand('%:p'),
                \ 'typed': strpart(getline('.'), 0, pos[2]-1),
                \ 'tick': ncm2#context_tick(),
                \ 'context_id': s:context_id,
                \ 'mode': mode()
                \ }
    if ctx.filepath == ''
        " FIXME this is necessary here, otherwise empty filepath is
        " somehow converted to None in vim8's python binding.
        let ctx.filepath = ''
    endif
    return ctx
endfunc

func! ncm2#register_source(sr)
    let sr = a:sr
    let name = sr.name

    " if registered before, ignore this call
    if has_key(s:sources, name)
        return
    endif

    let sr['enable'] = get(sr, 'enable', 1)
    let sr['ready'] = get(sr, 'ready', 1)
    let sr['priority'] = get(sr, 'priority', 5)
    let sr['auto_popup'] = get(sr, 'auto_popup', 1)
    let sr['early_cache'] = get(sr, 'early_cache', 0)
    let sr['subscope_enable'] = get(sr, 'subscope_enable', 0)
    if !has_key(sr, 'on_complete')
        throw "ncm2#register_source on_complete is required"
    endif

    let s:sources[name] = sr

    if has('nvim')
        call dictwatcheradd(sr, 'enable', 'ncm2#_on_enable')
        call dictwatcheradd(sr, 'ready', 'ncm2#_on_ready')
    endif

    call s:override_source(sr)
    call s:on_warmup(name)
endfunc

func! ncm2#override_source(name, v)
    if empty(a:v)
        if has_key(s:sources_override, a:name)
            unlet s:sources_override[a:name]
        endif
        return
    endif
    let s:sources_override[a:name] = a:v
    if has_key(s:sources, a:name)
        call s:override_source(s:sources[a:name])
    endif
endfunc

func! s:override_source(sr)
    if !has_key(s:sources_override, a:sr.name)
        return
    endif
    if type(s:sources_override[a:sr.name]) == v:t_dict
        call extend(a:sr, s:sources_override[a:sr.name])
    else
        call s:sources_override[a:sr.name](a:sr)
    endif
endfunc

func! ncm2#unregister_source(sr)
    let name = a:sr
    if type(a:sr) == v:t_dict
        let name = a:sr.name
    endif
    let sr = s:sources[name]

    if has('nvim')
        call dictwatcherdel(sr, 'enable', 'ncm2#_on_enable')
        call dictwatcherdel(sr, 'ready', 'ncm2#_on_ready')
    endif

    unlet s:sources[name]
endfunc

func! ncm2#_on_enable(sr, ...)
    if a:sr.enable
        call s:on_warmup(a:sr.name)
    endif
endfunc

func! ncm2#_on_ready(sr, ...)
    if a:sr.ready
        call s:on_warmup(a:sr.name)
    endif
endfunc

" deprecated
func! ncm2#set_ready(sr)
    let a:sr.ready = 1
endfunc

func! ncm2#context(name)
    return s:request('get_context', a:name)
endfunc

func! ncm2#complete(ctx, startccol, matches, ...)
    let refresh = get(a:000, 0, 0)
    call s:try_rnotify('complete',
            \   a:ctx,
            \   a:startccol,
            \   a:matches,
            \   refresh)
endfunc

func! ncm2#complete_resolve(ctx, item)
    if has_key(a:ctx, 'on_complete_resolved')
        call call(a:ctx.on_complete_resolved, [a:ctx, a:item])
    endif
endfunc

func! ncm2#complete_context_dated(ctx)
    return a:ctx.context_id < get(s:completion_notified, a:ctx.source, 0)
endfunc

func! ncm2#context_dated(ctx)
    " TODO remove deprecated function
    call s:core.error('deprecated function ncm2#context_dated called by source ' . string(a:ctx.source))
    return ncm2#complete_context_dated(a:ctx)
endfunc

func! ncm2#menu_selected()
    " Note: If arrow key is used instead of <c-n> and <c-p>,
    " ncm2#menu_selected will not work.
    return pumvisible() && !empty(v:completed_item)
endfunc

func! ncm2#completed_item()
    let item = copy(v:completed_item)
    if empty(item)
        return {}
    endif
    let ud = {}
    silent! let ud = json_decode(v:completed_item.user_data)
    if empty(ud) || type(ud) != v:t_dict
        return {}
    endif
    let item.user_data = ud
    if get(ud, 'ncm2', 0)
        return item
    else
        return {}
    endif
endfunc

func! ncm2#lock(name)
    let s:lock[a:name] = 1
endfunc

func! ncm2#unlock(name)
    unlet s:lock[a:name]
    if mode() == 'i'
        call ncm2#auto_trigger()
    endif
endfunc

func! ncm2#_update_matches(ctx, startbcol, matches)
    if g:ncm2#popup_delay
        let s:popup_timer_args = [a:ctx, a:startbcol, a:matches]
        if s:popup_timer
            if s:popup_timer_tick == a:ctx.tick
                return
            endif
            let s:popup_timer_tick = a:ctx.tick
            call timer_stop(s:popup_timer)
        endif
        let s:popup_timer = timer_start(g:ncm2#popup_delay,
                    \ funcref('s:popup_timed'))
    else
        call ncm2#_real_update_matches(a:ctx, a:startbcol, a:matches)
    endif
endfunc

func! s:popup_timed(_)
    let s:popup_timer = 0
    call call('ncm2#_real_update_matches', s:popup_timer_args)
endfunc

func! ncm2#_check_popup_close()
    " Defer the check for ncm2#auto_trigger
    if ncm2#context_tick() != s:auto_trigger_tick && !s:popup_close_check_state
        let s:popup_close_check_state = 1
        call ncm2#imode_task('ncm2#_check_popup_close')
        return ''
    endif
    " s:popup_close_check_state to prevent infinite ncm2#_check_popup_close
    " when s:auto_trigger_tick cannot be updated
    let s:popup_close_check_state = 0

    if s:popup_open && !pumvisible()
        silent doau <nomodeline> User Ncm2PopupClose
        let s:popup_open = 0
        let s:popup_closed_by_user = !empty(s:matches)
        let s:popup_close_tick = ncm2#context_tick()
        call s:cache_matches_cleanup()
    endif
    return ''
endfunc

func! ncm2#_real_update_matches(ctx, startbcol, matches)
    if ncm2#context_tick() != a:ctx.tick
        return
    endif

    let s:startbcol = a:startbcol
    let s:matches = a:matches
    let s:lnum = a:ctx.lnum

    call ncm2#_real_popup()
endfunc

func! ncm2#_real_popup(...)
    if s:should_skip()
        return
    endif

    " If popup menu is closed by user
    if !s:popup_open && s:popup_closed_by_user && s:popup_close_tick == ncm2#context_tick()
        return
    endif

    let pos = getcurpos()
    if s:lnum != pos[1]
        let s:lnum = pos[1]
        let s:matches = []
    endif
    if pos[2] < s:startbcol
        let s:matches = []
    endif

    if ncm2#menu_selected()
        return ''
    endif

    if empty(s:matches)
        " this enables the vanilla <c-n> and <c-p> keys behavior when
        " there's no popup
        if pumvisible() && s:popup_open
            call feedkeys("\<Plug>(ncm2_c_e)", "mi")
        endif
        return ''
    endif

    let s:popup_open = 1
    silent doau <nomodeline> User Ncm2PopupOpen
    call complete(s:startbcol, s:matches)
    return ''
endfunc

func! ncm2#skip_auto_trigger()
    " deprecated
    return ''
endfunc

func! ncm2#auto_trigger()
    let tick = ncm2#context_tick()
    if tick == s:auto_trigger_tick
        return ''
    endif
    let s:auto_trigger_tick = tick

    " refresh the popup menu to reduce popup flickering
    call ncm2#_real_popup()

    if g:ncm2#complete_delay == 0
        call ncm2#do_auto_trigger()
    else
        if s:complete_timer
            call timer_stop(s:complete_timer)
        endif
        let s:complete_timer = timer_start(g:ncm2#complete_delay,
                \ 'ncm2#_complete_timer_handler')
    endif
    return ''
endfunc

func! ncm2#_complete_timer_handler(...)
    let s:complete_timer = 0
    call ncm2#do_auto_trigger()
endfunc

func! ncm2#do_auto_trigger()
    if s:should_skip()
        return
    endif
    call s:try_rnotify('on_complete', 0)
endfunc

func! ncm2#manual_trigger(...)
    call s:try_rnotify('on_complete', 1, a:000)
    return ''
endfunc

func! ncm2#force_trigger(...)
    call s:try_rnotify('on_complete', 2, a:000)
    return ''
endfunc

func! ncm2#_notify_complete(ctx, calls)
    if ncm2#context_tick() != a:ctx.tick
        if !s:should_skip()
            call s:try_rnotify('on_notify_dated', a:ctx, a:calls)
        endif
        return
    endif
    for ele in a:calls
        let name = ele['name']
        try
            let s:completion_notified[name] = a:ctx.context_id
            let sr = s:sources[name]
            let ctx = ele.context
            if type(sr.on_complete) == v:t_list
                call call(sr.on_complete[0], sr.on_complete[1:] + [ctx], sr)
            else
                call call(sr.on_complete, [ctx], sr)
            endif
        catch
            call s:core.error(name . ' on_complete: ' . v:exception)
        endtry
    endfor
endfunc

func! ncm2#_notify_completed(ctx, name, sctx, completed)
    let s:completion_notified[a:name] = a:sctx.context_id
    let a:sctx.dated = 0
    let sr = s:sources[a:name]
    call call(sr.on_completed, [a:sctx, a:completed], sr)
endfunc

func! ncm2#_warmup_sources(ctx, calls)
    if bufnr('%') != a:ctx.bufnr
        " the user has switched to another buffer
        return
    endif
    if &modifiable == 0
        " temrinal buffers, and special buffers created by plugins (gina,
        " fugitive, etc.)
        return
    endif
    for ele in a:calls
        let name = ele['name']
        try
            let sr = s:sources[name]
            if !has_key(sr, 'on_warmup')
                continue
            endif
            let ctx = ele.context
            call call(sr.on_warmup, [ctx], sr)
        catch
            call s:core.error(name . ' on_warmup: ' . v:exception)
        endtry
    endfor
endfunc

func! ncm2#_s(name, ...)
    if len(a:000)
        execute 'let s:' . a:name ' = a:1'
    endif
    return get(s:, a:name)
endfunc

func! s:coredata(event)
    " data sync between ncm2.vim and ncm2_core.py
    let data = { 'event': a:event,
                \ 'auto_popup': g:ncm2#auto_popup,
                \ 'complete_length': g:ncm2#complete_length,
                \ 'manual_complete_length': g:ncm2#manual_complete_length,
                \ 'matcher': g:ncm2#matcher,
                \ 'sorter': g:ncm2#sorter,
                \ 'filter': g:ncm2#filter,
                \ 'popup_limit': g:ncm2#popup_limit,
                \ 'total_popup_limit': g:ncm2#total_popup_limit,
                \ 'context': s:context(),
                \ 'sources': s:sources,
                \ 'whitelist_for_buffer': ncm2#whitelist_for_buffer(),
                \ 'blacklist_for_buffer': ncm2#blacklist_for_buffer(),
                \ 'subscope_detectors': s:subscope_detectors,
                \ 'lines': []
                \ }
    return s:do_coredata_hook(a:event, data)
endfunc

func! ncm2#_hook_for_subscope_detectors()
    if !get(b:, 'ncm2_enable', 0) || !has_key(s:subscope_detectors, &filetype)
        let Hook = v:null
    else
        let Hook = {d -> extend(d, {"lines":getline(1, '$')}, "force")}
    endif
    let events = ['on_complete', 'get_context', 'on_warmup']
    call ncm2#hook_coredata(0, events, 'subscope_detectors', Hook)
endfunc

func! s:b_coredata_hooks()
    if has_key(b:, 'ncm2_coredata_hooks')
        return b:ncm2_coredata_hooks
    else
        let b:ncm2_coredata_hooks = {}
        return b:ncm2_coredata_hooks
    endif
endfunc

func! ncm2#hook_coredata(is_global, events, groupid, Hook)
    let hooks = a:is_global ? s:coredata_hooks : s:b_coredata_hooks()
    let events = type(a:events) == v:t_string ? [a:events] : a:events
    for event in events
        let hooks[event] = get(hooks, event, {})
        if a:Hook is v:null
            if has_key(hooks[event], a:groupid)
                unlet hooks[event][a:groupid]
            endif
        else
            let hooks[event][a:groupid] = a:Hook
        endif
    endfor
endfunc

func! s:do_coredata_hook(event, data)
    let [event, data] = [a:event, a:data]
    let hooks = values(get(s:coredata_hooks, event, {})) +
                \ values(get(s:b_coredata_hooks(), event, {}))
    for Hook in hooks
        let data = Hook(data)
    endfor
    return data
endfunc

func! s:try_rnotify(event, ...)
    let args = [a:event, s:coredata(a:event)] + a:000
    return call(s:core.try_notify, args, s:core)
endfunc

func! s:request(event, ...)
    let args = [a:event, s:coredata(a:event)] + a:000
    return call(s:core.request, args, s:core)
endfunc

func! s:on_warmup(...)
    if !get(b:, 'ncm2_enable', 0)
        return
    endif

    call ncm2#_hook_for_subscope_detectors()

    call s:try_rnotify('on_warmup', a:000)
endfunc

func! ncm2#_core_started()
    call s:try_rnotify('load_plugin', &rtp)
    call s:on_warmup()
endfunc

func! ncm2#_load_vimscript(s)
    try
        execute 'source ' . a:s
    catch
        call s:core.error(a:s . ': ' . v:exception)
    endtry
endfunc

func! ncm2#_au_plugin()
    try
        au User Ncm2Plugin silent
        doau <nomodeline> User Ncm2Plugin
        au! User Ncm2Plugin
    catch
        call s:core.error(v:exception)
    endtry

    if has_key(s:subscope_detectors, &filetype)
        call s:on_warmup()
    endif
endfunc

func! ncm2#insert_mode_only_key(key)
    exe 'map' a:key '<nop>'
    exe 'cmap' a:key '<nop>'
    if exists(':tmap')
        exe 'tmap' a:key '<nop>'
    endif
endfunc

func! s:should_skip()
    return !get(b:,'ncm2_enable',0) || &paste || !empty(s:lock) || mode()!='i'
endfunc

func! ncm2#on_waiting_input(fn, ...)
    let args = a:000
    " The callback is only invoked when Vim is waiting for input.
    call timer_start(0, function('s:do_on_waiting_input', [a:fn, args]))
endfunc

func! s:do_on_waiting_input(fn, args, timer)
    call call(a:fn, a:args)
endfunc

func! ncm2#imode_task(fn, ...)
    let args = a:000
    " The callback is only invoked when Vim is waiting for input.
    call timer_start(0, function('s:do_imode_task', [a:fn, args]))
endfunc

func! s:do_imode_task(fn, args, timer)
    if s:should_skip()
        return
    endif
    call call(a:fn, a:args)
endfunc

func! ncm2#whitelist_for_buffer(...)
    let b:ncm2_whitelist = get(b:, 'ncm2_whitelist', [])
    if a:0
        let b:ncm2_whitelist = type(a:1) == v:t_string ? a:000 : a:1
    endif
    return b:ncm2_whitelist
endfunc

func! ncm2#blacklist_for_buffer(...)
    let b:ncm2_blacklist = get(b:, 'ncm2_blacklist', [])
    if a:0
        let b:ncm2_blacklist = type(a:1) == v:t_string ? a:000 : a:1
    endif
    return b:ncm2_blacklist
endfunc

call ncm2#insert_mode_only_key('<Plug>(ncm2_skip_auto_trigger)')
call ncm2#insert_mode_only_key('<Plug>(ncm2_auto_trigger)')
call ncm2#insert_mode_only_key('<Plug>(ncm2_manual_trigger)')
call ncm2#insert_mode_only_key('<Plug>(ncm2_c_e)')

" func! s:dbg(str)
"     echom a:str . ' ' . json_encode(ncm2#context_tick())
" endfunc
