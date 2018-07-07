if get(s:,'loaded','0')
    finish
endif
let s:loaded = 1

func! s:opt(name, default)
    let val = get(g:, a:name, a:default)
    let cmd = 'let g:' . a:name . '= l:val'
    execute cmd
endfunc

call s:opt('ncm2#auto_popup', 1)
call s:opt('ncm2#complete_delay', 0)
call s:opt('ncm2#popup_delay', 100)
call s:opt('ncm2#complete_length', [[1,4],[7,3]])
call s:opt('ncm2#matcher', 'prefix')
call s:opt('ncm2#sorter', 'swapcase_word')
call s:opt('ncm2#filter', [])

let g:ncm2#core_data = {}
let g:ncm2#core_event = {}

inoremap <silent> <Plug>(ncm2_auto_trigger) <C-r>=ncm2#_auto_trigger()<CR>
inoremap <silent> <Plug>(ncm2_manual_trigger) <C-r>=ncm2#_trigger(1)<CR>

" use silent mapping that doesn't slower the terminal ui
" Note: `:help complete()` says:
" > You need to use a mapping with CTRL-R = |i_CTRL-R|.  It does not work
" > after CTRL-O or with an expression mapping.
inoremap <silent> <Plug>(ncm2_complete_popup) <C-r>=ncm2#_complete_popup()<CR>
inoremap <silent> <Plug>(_ncm2_auto_trigger) <C-r>=ncm2#_trigger(0)<CR>

let s:core = yarp#py3('ncm2_core')
let s:sources = {}
let s:popup_timer = 0
let s:complete_timer = 0
let s:lock = {}
let s:startbcol = 1
let s:lnum = 0
let s:matches = []
let s:subscope_detectors = {}
let s:auto_complete_tick = []

augroup ncm2_hooks
    autocmd!
    autocmd User Ncm2EnableForBufferPre,Ncm2EnableForBufferPost silent
    autocmd User Ncm2CoreData silent 
    autocmd OptionSet runtimepath call s:try_rnotify('load_plugin', &rtp)
augroup END

func! ncm2#enable_for_buffer()
    doautocmd User Ncm2EnableForBufferPre

    let b:ncm2_enable = 1

    augroup ncm2_buf_hooks
        autocmd! * <buffer>
        autocmd InsertLeave <buffer> call s:cache_cleanup()
        autocmd BufEnter,CursorHold <buffer> call s:warmup()
        autocmd InsertEnter,TextChangedI,InsertCharPre <buffer> call ncm2#auto_trigger()
    augroup END

    call s:core.jobstart()
    call s:warmup()

    doautocmd User Ncm2EnableForBufferPost
endfunc

func! s:cache_cleanup()
    let s:matches = []
    let s:auto_complete_tick = []
    let s:lnum = 0
    let s:startbcol = 1
    call s:try_rnotify('cache_cleanup')
endfunc

func! ncm2#disable_for_buffer()
    let b:ncm2_enable = 0
    augroup ncm2_buf_hooks
        autocmd! * <buffer>
    augroup END
endfunc

func! ncm2#context(...)
    let ctx = {'bufnr':bufnr('%'), 'curpos':getcurpos(), 'changedtick':b:changedtick}
    let ctx['lnum'] = ctx['curpos'][1]
    let ctx['bcol'] = ctx['curpos'][2]
    let ctx['filetype'] = &filetype
    let ctx['scope'] = &filetype
    let ctx['filepath'] = expand('%:p')
    if ctx['filepath'] == ''
        " FIXME this is necessary here, otherwise empty filepath is
        " somehow converted to None in vim's python binding.
        let ctx['filepath'] = ""
    endif
    let ctx['typed'] = strpart(getline(ctx['lnum']), 0, ctx['bcol']-1)
    let ctx['ccol'] = strchars(ctx['typed']) + 1
    if len(a:000)
        let ctx['source'] = a:1
    endif
    let ctx['reltime'] = reltimefloat(reltime())
    return ctx
endfunc

func! ncm2#context_dated(ctx)
    return getcurpos() != a:ctx.curpos ||
        \ b:changedtick != a:ctx.changedtick
endfunc

func! ncm2#register_source(sr)
    let sr = a:sr
    let name = sr.name

    " if registered before, ignore this call
    if has_key(s:sources, name)
        return
    endif

    let sr['enable'] = get(sr, 'enable', 1)
    let sr['priority'] = get(sr, 'priority', 5)
    let sr['auto_popup'] = get(sr, 'auto_popup', 1)
    let sr['early_cache'] = get(sr, 'early_cache', 0)
    let sr['subscope_enable'] = get(sr, 'subscope_enable', 0)
    if !has_key(sr, 'on_complete')
        throw "ncm2#register_source on_complete is required"
    endif
    " these fields are allowed to be zero/empty
    "   complete_pattern: []
    "   complete_length
    "   on_warmup

    let s:sources[name] = sr

    call s:warmup()
endfunc

func! ncm2#disable_source(name)
    try
        let s:sources[a:name]['enable'] = 0
    catch
        call s:core.error(v:exception)
    endtry
endfunc

func! ncm2#complete(ctx, startccol, matches, ...)
    let refresh = 0
    if len(a:000)
        let refresh = a:1
    endif

    let dated = ncm2#context_dated(a:ctx)
    let a:ctx.dated = dated

    call s:try_rnotify('complete',
            \   a:ctx,
            \   a:startccol,
            \   a:matches,
            \   refresh)

    if dated && refresh
        call ncm2#_trigger(2)
    endif
endfunc

func! ncm2#menu_selected()
    " when the popup menu is visible, v:completed_item will be the
    " current_selected item
    "
    " if v:completed_item is empty, no item is selected
    "
    " Note: If arrow key is used instead of <c-n> and <c-p>,
    " ncm2#menu_selected will not work.
    return pumvisible() && !empty(v:completed_item)
endfunc

" useful when working with other plugins
func! ncm2#lock(name)
    let s:lock[a:name] = 1
endfunc

func! ncm2#unlock(name)
    unlet s:lock[a:name]
endfunc

func! ncm2#_popup(ctx, startbcol, matches)
    if s:popup_timer
        call timer_stop(s:popup_timer)
        let s:popup_timer = 0
    endif
    if g:ncm2#popup_delay && !pumvisible()
        let s:popup_timer = timer_start(
            \ g:ncm2#popup_delay,
            \ {_ -> s:popup_timed(
            \           a:ctx,
            \           a:startbcol,
            \           a:matches) })
    else
        call s:do_popup(a:ctx, a:startbcol, a:matches)
    endif
endfunc

func! s:popup_timed(ctx, startbcol, matches)
    let s:popup_timer = 0
    call s:do_popup(a:ctx, a:startbcol, a:matches)
endfunc

func! s:do_popup(ctx, startbcol, matches)
    let shown = pumvisible()

    " When the popup menu is expected to be displayed but it is not, I
    " guess it probably has been closed by the user
    if !shown && !empty(s:matches) && !empty(a:matches)
        return
    endif

    let s:startbcol = a:startbcol
    let s:matches = a:matches
    let s:lnum = a:ctx.lnum

    if s:should_skip()
        return
    endif

    " from core channel
    " something selected by user, do not refresh the menu
    if ncm2#menu_selected()
        return
    endif

    call s:feedkeys("\<Plug>(ncm2_complete_popup)")
endfunc

func! ncm2#_complete_popup()
    if s:lnum != getcurpos()[1]
        let s:lnum = getcurpos()[1]
        let s:matches = []
    endif
    call complete(s:startbcol, s:matches)
    return ''
endfunc

func! s:should_skip()
    return !get(b:,'ncm2_enable',0) ||
                \ &paste != 0 ||
                \ !empty(s:lock) ||
                \ mode() != 'i'
endfunc

func! ncm2#auto_trigger()
    " Use feedkeys, to makesure that the auto complete check works for autocmd
    " InsertEnter, it is not yet in insert mode at the time.
    call s:feedkeys("\<Plug>(ncm2_auto_trigger)")
endfunc

func! ncm2#_auto_trigger()
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
    call s:feedkeys("\<Plug>(_ncm2_auto_trigger)")
endfunc

" 0 auto, 1 manual, 2 auto for dated source
func! ncm2#_trigger(trigger_type)
    if s:should_skip()
        return ''
    endif

    let l:manual = a:trigger_type == 1
    if l:manual == 0
        if g:ncm2#auto_popup == 0
            return ''
        endif

        " not auto for dated source, no need duplicate on_complete
        if a:trigger_type != 2
            let tick = [getcurpos(), b:changedtick]
            if tick == s:auto_complete_tick
                return ''
            endif
            let s:auto_complete_tick = tick
        endif
    endif

    call s:try_rnotify('on_complete', l:manual)
    return ''
endfunc

func! ncm2#_notify_sources(ctx, calls)
    if ncm2#context_dated(a:ctx) && !get(a:ctx, 'manual', 0)
        " better to refresh
        call s:try_rnotify('on_complete', 0, a:calls)
    endif
    for ele in a:calls
        let name = ele['name']
        try
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

func! ncm2#_warmup_sources(calls)
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
                \ 'complete_length': g:ncm2#complete_length,
                \ 'matcher': g:ncm2#matcher,
                \ 'sorter': g:ncm2#sorter,
                \ 'filter': g:ncm2#filter,
                \ 'context': ncm2#context(),
                \ 'sources': s:sources,
                \ 'subscope_detectors': s:subscope_detectors,
                \ 'lines': []
                \ }, 'force')

    " if subscope detector is available for this buffer, we need to send
    " the whole buffer for on_complete event
    if (a:event == 'on_complete' || a:event == 'on_warmup') &&
                \ has_key(s:subscope_detectors, &filetype)
        let data.lines = getline(1, '$')
    endif

    return data
endfunc

func! s:try_rnotify(event, ...)
    let g:ncm2#core_event = [a:event, a:000]
    let g:ncm2#core_data = {}
    doautocmd User Ncm2CoreData
    let data = ncm2#_core_data(a:event)
    let g:ncm2#core_data = {}
    let g:ncm2#core_event = []
    return call(s:core.try_notify, [a:event, data] + a:000, s:core)
endfunc

func! s:warmup()
    if !get(b:, 'ncm2_enable', 0)
        return
    endif
    call s:try_rnotify('on_warmup')
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

func! ncm2#_load_python(py)
    call s:try_rnotify('load_python', a:py)
endfunc

func! ncm2#_autocmd_plugin()
    autocmd User Ncm2Plugin silent
    doautocmd User Ncm2Plugin
    autocmd! User Ncm2Plugin
endfunc

func! s:feedkeys(key)
    if &paste
        return
    endif
    call feedkeys(a:key, 'im')
endfunc

if g:ncm2#auto_popup && stridx(&completeopt, 'noinsert') == -1
    call s:core.error("auto-popup requries `:set completeopt+=noinsert`")
endif
if g:ncm2#auto_popup && stridx(&completeopt, 'longest') != -1
    call s:core.error("auto-popup requries `:set completeopt-=longest`")
endif
