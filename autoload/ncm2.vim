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
call s:opt('ncm2#matcher', 'abbrfuzzy')
call s:opt('ncm2#sorter', 'abbrfuzzy')
call s:opt('ncm2#filter', [])
call s:opt('ncm2#popup_limit', -1)

let g:ncm2#core_data = {}
let g:ncm2#core_event = []

inoremap <silent> <Plug>(ncm2_skip_auto_trigger) <C-r>=ncm2#skip_auto_trigger()<CR>
inoremap <silent> <Plug>(ncm2_auto_trigger) <C-r>=ncm2#_do_auto_trigger()<CR>
inoremap <silent> <Plug>(ncm2_manual_trigger) <C-r>=ncm2#_on_complete(1)<CR>

" use silent mapping that doesn't slower the terminal ui
" Note: `:help complete()` says:
" > You need to use a mapping with CTRL-R = |i_CTRL-R|.  It does not work
" > after CTRL-O or with an expression mapping.
inoremap <silent> <Plug>(ncm2_complete_popup) <C-r>=ncm2#_real_popup()<CR>
inoremap <silent> <Plug>(_ncm2_auto_trigger) <C-r>=ncm2#_on_complete(0)<CR>

let s:core = yarp#py3('ncm2_core')
let s:core.on_load = 'ncm2#_core_started'
let s:sources = {}
let s:sources_override = {}
let s:popup_timer = 0
let s:popup_timer_args = []
let s:popup_timer_tick = []
let s:complete_timer = 0
let s:lock = {}
let s:startbcol = 1
let s:lnum = 0
let s:matches = []
let s:subscope_detectors = {}
let s:auto_trigger_tick = []
let s:skip_tick = []
let s:skip_context_id = 0
let s:context_tick_extra = 0
let s:context_id = 0
let s:completion_notified = {}

augroup ncm2_hooks
    au!
    au User Ncm2EnableForBuffer call s:warmup()
    au User Ncm2CoreData,Ncm2PopupClose,Ncm2PopupOpen silent 
    au FileType * call s:try_rnotify('load_plugin', &rtp)
augroup END

func! ncm2#enable_for_buffer()
    if get(b:, 'ncm2_enable', 0)
        return
    endif
    let b:ncm2_enable = 1

    augroup ncm2_buf_hooks
        au! * <buffer>
        au Insertenter,InsertLeave <buffer> call s:cache_cleanup()
        au BufEnter <buffer> call s:warmup()
        au InsertEnter,InsertCharPre,TextChangedI <buffer> call ncm2#auto_trigger()
        if has("patch-8.0.1493")
            au CompleteDone <buffer> call s:on_complete_done()
        endif
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
    if empty(v:completed_item)
        return
    endif
    " The user has accepted the item, don't popup old s:matches again.
    call ncm2#skip_auto_trigger()
    call s:try_rnotify('on_complete_done', v:completed_item)
endfunc

func! s:cache_cleanup()
    call s:cache_matches_cleanup()
    let s:auto_trigger_tick  = []
    let s:skip_tick = []
    call s:try_rnotify('cache_cleanup')
endfunc

func! s:cache_matches_cleanup()
    let s:matches = []
    let s:lnum = 0
    let s:startbcol = 1
endfunc

func! s:context_tick()
    " FIXME b:changedtick ticks when <c-y> is typed.  curswant of
    " getcurpos() also ticks sometimes after <c-y> is typed. Use cursor
    " position to filter the requests.
    return [getcurpos()[0:2], s:context_tick_extra]
endfunc

func! s:context()
    let s:context_id += 1
    let pos = getcurpos()
    let bcol = pos[2]
    let typed = strpart(getline('.'), 0, bcol-1)
    let ctx = {
                \ 'bufnr': bufnr('%'),
                \ 'curpos': pos,
                \ 'changedtick': b:changedtick,
                \ 'lnum': pos[1],
                \ 'bcol': bcol,
                \ 'ccol': strchars(typed) + 1,
                \ 'filetype': &filetype,
                \ 'scope': &filetype,
                \ 'filepath': expand('%:p'),
                \ 'typed': strpart(getline('.'), 0, pos[2]-1),
                \ 'tick': s:context_tick(),
                \ 'context_id': s:context_id
                \ }
    if ctx.filepath == ''
        " FIXME this is necessary here, otherwise empty filepath is
        " somehow converted to None in vim8's python binding.
        let ctx.filepath = ""
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
    call s:warmup(name)
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
        call s:warmup(a:sr.name)
    endif
endfunc

func! ncm2#_on_ready(sr, ...)
    if a:sr.ready
        call s:warmup(a:sr.name)
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
    let refresh = 0
    if len(a:000)
        let refresh = a:1
    endif

    let dated = s:context_tick() != a:ctx.tick
    let a:ctx.dated = dated

    call s:try_rnotify('complete',
            \   a:ctx,
            \   a:startccol,
            \   a:matches,
            \   refresh)

    if dated && refresh
        call ncm2#_on_complete(2)
    endif
endfunc

func! ncm2#context_dated(ctx)
    return a:ctx.context_id < get(s:completion_notified, a:ctx.source.name, 0)
endfunc

func! ncm2#menu_selected()
    " Note: If arrow key is used instead of <c-n> and <c-p>,
    " ncm2#menu_selected will not work.
    return pumvisible() && !empty(v:completed_item)
endfunc

func! ncm2#lock(name)
    call ncm2#skip_auto_trigger()
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

func! ncm2#_real_update_matches(ctx, startbcol, matches)
    if s:context_tick() != a:ctx.tick
        return
    endif

    " The popup is expected to be opened while it has been closed
    if !empty(s:matches) && !pumvisible()
        if empty(v:completed_item)
            " the user closed the popup with <c-e>
            " TODO suppress future completion unless another word started
            call s:cache_matches_cleanup()
            return
        else
            " this should have been handled in CompleteDone, but we have newer
            " matches now. It's ok to proceed
        endif
    endif

    let s:startbcol = a:startbcol
    let s:matches = a:matches
    let s:lnum = a:ctx.lnum

    call s:feedkeys("\<Plug>(ncm2_complete_popup)")
endfunc

func! ncm2#_real_popup()
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
        if pumvisible()
            call s:feedkeys("\<c-e>", "ni")
        endif
        doau <nomodeline> User Ncm2PopupClose
        return ''
    endif

    doau <nomodeline> User Ncm2PopupOpen
    call complete(s:startbcol, s:matches)
    return ''
endfunc

func! ncm2#skip_auto_trigger()
    call s:cache_matches_cleanup()
    " invalidate s:update_matches
    " invalidate ncm2#_notify_complete
    let s:context_tick_extra += 1
    " skip auto ncm2#_on_complete
    let s:skip_tick = s:context_tick()
    doau <nomodeline> User Ncm2PopupClose
    if pumvisible()
        call s:feedkeys("\<Plug>(ncm2_complete_popup)", 'im')
    endif
    return ''
endfunc

func! ncm2#auto_trigger()
    if &paste
        return
    endif
    " Use feedkeys, to make sure that the auto complete check works for au
    " InsertEnter, it is not yet in insert mode at the time.
    call s:feedkeys("\<Plug>(ncm2_auto_trigger)")
endfunc

func! ncm2#_do_auto_trigger()
    let tick = s:context_tick()
    if tick == s:auto_trigger_tick
        return ''
    endif
    let s:auto_trigger_tick = tick

    " refresh the popup menu to reduce popup flickering
    call s:feedkeys("\<Plug>(ncm2_complete_popup)")

    if g:ncm2#complete_delay == 0
        call s:feedkeys("\<Plug>(_ncm2_auto_trigger)")
    else
        if s:complete_timer
            call timer_stop(s:complete_timer)
        endif
        let s:complete_timer = timer_start(
            \ g:ncm2#complete_delay,
            \ {_ -> s:complete_timer_handler() })
    endif
    return ''
endfunc

func! s:complete_timer_handler()
    if &paste
        return
    endif
    let s:complete_timer = 0
    if mode() == 'i'
        call s:feedkeys("\<Plug>(_ncm2_auto_trigger)")
    endif
endfunc

func! ncm2#_on_complete(trigger_type)
    let l:manual = a:trigger_type == 1
    if l:manual == 0
        if g:ncm2#auto_popup == 0
            return ''
        endif
        if s:skip_tick == s:context_tick()
            return ''
        endif
    endif

    " skip_tick is dated, we don't need it anymore
    let s:skip_tick = []
    call s:try_rnotify('on_complete', l:manual)
    return ''
endfunc

func! ncm2#_notify_complete(ctx, calls)
    if s:context_tick() != a:ctx.tick
        call s:try_rnotify('on_notify_dated', a:ctx, a:calls)
        " we need skip check, and auto_popup check in ncm2#_on_complete
        " we don't need duplicate check in ncm2#auto_trigger
        call ncm2#_on_complete(get(a:ctx, 'manual', 0))
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
    if s:context_tick() != a:ctx.tick
        return
    endif
    let s:completion_notified[a:name] = a:sctx.context_id
    let a:sctx.dated = 0
    let sr = s:sources[a:name]
    call call(sr.on_completed, [a:sctx, a:completed], sr)
endfunc

func! ncm2#_warmup_sources(ctx, calls)
    if bufnr('%') != a:ctx.bufnr
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

func! ncm2#_core_data(event)
    " data sync between ncm2.vim and ncm2_core.py
    let data = extend(g:ncm2#core_data, {
                \ 'auto_popup': g:ncm2#auto_popup,
                \ 'skip_tick': s:skip_tick,
                \ 'complete_length': g:ncm2#complete_length,
                \ 'matcher': g:ncm2#matcher,
                \ 'sorter': g:ncm2#sorter,
                \ 'filter': g:ncm2#filter,
                \ 'popup_limit': g:ncm2#popup_limit,
                \ 'context': s:context(),
                \ 'sources': s:sources,
                \ 'subscope_detectors': s:subscope_detectors,
                \ 'lines': []
                \ }, 'force')

    " if subscope detector is available for this buffer, we need to send
    " the whole buffer for on_complete event
    if has_key(s:subscope_detectors, &filetype) &&
                \ (a:event == 'on_complete' ||
                \ a:event == 'get_context' ||
                \ a:event == 'on_warmup' ||
                \ a:event == 'on_complete_done')
        let data.lines = getline(1, '$')
    endif

    return data
endfunc

func! s:try_rnotify(event, ...)
    let g:ncm2#core_event = [a:event, a:000]
    let g:ncm2#core_data = {}
    doau <nomodeline> User Ncm2CoreData
    let data = ncm2#_core_data(a:event)
    let g:ncm2#core_data = {}
    let g:ncm2#core_event = []
    return call(s:core.try_notify, [a:event, data] + a:000, s:core)
endfunc

func! s:request(event, ...)
    let g:ncm2#core_event = [a:event, a:000]
    let g:ncm2#core_data = {}
    doau <nomodeline> User Ncm2CoreData
    let data = ncm2#_core_data(a:event)
    let g:ncm2#core_data = {}
    let g:ncm2#core_event = []
    return call(s:core.request, [a:event, data] + a:000, s:core)
endfunc

func! s:warmup(...)
    if !get(b:, 'ncm2_enable', 0)
        return
    endif
    call s:try_rnotify('on_warmup', a:000)
    " the FZF terminal window somehow gets empty without this check
    " https://github.com/ncm2/ncm2/issues/50
    if mode() == 'i'
        call s:feedkeys("\<Plug>(_ncm2_auto_trigger)")
    endif
endfunc

func! ncm2#_core_started()
    call s:try_rnotify('load_plugin', &rtp)
    call s:warmup()
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
        call s:warmup()
    endif
endfunc

func! s:feedkeys(key, ...)
    if !get(b:,'ncm2_enable',0) ||
                \ &paste != 0 ||
                \ !empty(s:lock)
        return
    endif
    let m = 'm'
    if len(a:000)
        let m = a:1
    endif
    call feedkeys(a:key, m)
endfunc

func! ncm2#insert_mode_only_key(key)
    exe 'map' a:key '<nop>'
    exe 'cmap' a:key '<nop>'
    if exists(':tmap')
        exe 'tmap' a:key '<nop>'
    endif
endfunc

call ncm2#insert_mode_only_key('<Plug>(ncm2_skip_auto_trigger)')
call ncm2#insert_mode_only_key('<Plug>(ncm2_auto_trigger)')
call ncm2#insert_mode_only_key('<Plug>(ncm2_manual_trigger)')
call ncm2#insert_mode_only_key('<Plug>(ncm2_complete_popup)')
call ncm2#insert_mode_only_key('<Plug>(_ncm2_auto_trigger)')
