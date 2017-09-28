
let g:cm#snippet#snippets = []

func! cm#snippet#init()
	if ((!exists('g:cm_completed_snippet_enable') || g:cm_completed_snippet_enable) && !exists('g:cm_completed_snippet_engine'))
        if exists('g:loaded_neosnippet')
            let g:cm_completed_snippet_enable = 1
            let g:cm_completed_snippet_engine = 'neosnippet'
        elseif exists('g:did_plugin_ultisnips')
            let g:cm_completed_snippet_enable = 1
            let g:cm_completed_snippet_engine = 'ultisnips'
        elseif exists('g:snipMateSources')
            let g:cm_completed_snippet_enable = 1
            let g:cm_completed_snippet_engine = 'snipmate'
        else
            let g:cm_completed_snippet_enable = 0
            let g:cm_completed_snippet_engine = ''
        endif
    endif

    let g:cm_completed_snippet_enable = get(g:, 'cm_completed_snippet_enable', 0)
    let g:cm_completed_snippet_engine = get(g:, 'cm_completed_snippet_engine', '')

    if g:cm_completed_snippet_engine == 'neosnippet'
        call s:neosnippet_init()
    endif
    if g:cm_completed_snippet_engine == 'snipmate'
        call s:snipmate_init()
    endif
endfunc

func! cm#snippet#completed_is_snippet()
    call cm#snippet#check_and_inject()
    return get(v:completed_item, 'is_snippet', 0)
endfunc

func! cm#snippet#check_and_inject()

    if empty(v:completed_item) || !has_key(v:completed_item,'info') || empty(v:completed_item.info) || has_key(v:completed_item, 'is_snippet')
		return ''
	endif

	let l:last_line = split(v:completed_item.info,'\n')[-1]
	if l:last_line[0:len('snippet@')-1]!='snippet@'
        let v:completed_item.is_snippet = 0
		return ''
	endif

	let l:snippet_id = str2nr(l:last_line[len('snippet@'):])
	if l:snippet_id>=len(g:cm#snippet#snippets) || l:snippet_id<0
        let v:completed_item.is_snippet = 0
		return ''
	endif

	" neosnippet recognize the snippet field of v:completed_item. Also useful
	" for checking. Kind of a hack.
    " TODO: skip empty g:cm#snippet#snippets[l:snippet_id]['snippet']
	let v:completed_item.snippet = g:cm#snippet#snippets[l:snippet_id]['snippet']
    let v:completed_item.snippet_word = g:cm#snippet#snippets[l:snippet_id]['word']
    let v:completed_item.is_snippet = 1

    if v:completed_item.snippet == ''
        return ''
    endif

	if g:cm_completed_snippet_engine == 'ultisnips'

        call s:ultisnips_inject()

    " elseif g:cm_completed_snippet_engine == 'snipmate'
        " nothing needs to be done for snipmate

    elseif g:cm_completed_snippet_engine == 'neosnippet'

        call s:neosnippet_inject()

	endif

    return ''
endfunc

func! s:ultisnips_inject()
    if get(b:,'_cm_us_setup',0)==0
        " UltiSnips_Manager.add_buffer_filetypes('%s.snips.ncm' % vim.eval('&filetype'))
        let b:_cm_us_setup = 1
        let b:_cm_us_filetype = 'ncm'
        call UltiSnips#AddFiletypes(b:_cm_us_filetype)
        augroup cm
            autocmd InsertLeave <buffer> exec g:_uspy 'UltiSnips_Manager._added_snippets_source._snippets["ncm"]._snippets = []'
        augroup END
    endif
    exec g:_uspy 'UltiSnips_Manager._added_snippets_source._snippets["ncm"]._snippets = []'
    call UltiSnips#AddSnippetWithPriority(v:completed_item.snippet_word, v:completed_item.snippet, '', 'i', b:_cm_us_filetype, 1)
endfunc

func! s:neosnippet_init()
    " Not compatible with neosnippet#enable_completed_snippet. NCM
    " choose a different approach
    let g:neosnippet#enable_completed_snippet=0
    augroup cm
        autocmd InsertEnter * call s:neosnippet_cleanup()
    augroup END
    let s:neosnippet_injected = []
endfunc

func! s:neosnippet_inject()
    let snippets = neosnippet#variables#current_neosnippet()

    let item = {}
    let item['options'] = { "word": 1, "oneshot": 0, "indent": 0, "head": 0}
    let item['word'] = v:completed_item.snippet_word
    let item['snip'] = v:completed_item.snippet
    let item['description'] = ''

    let snippets.snippets[v:completed_item.snippet_word] = item

    " remember for cleanup
    let s:neosnippet_injected = add(s:neosnippet_injected, v:completed_item.snippet_word)
endfunc

func! s:neosnippet_cleanup()
    let cs = neosnippet#variables#current_neosnippet()
    for word in s:neosnippet_injected
        unlet cs.snippets[word]
    endfor
    let s:neosnippet_injected = []
endfunc

func! s:snipmate_init()
    " inject ncm's handler into snipmate
    let g:snipMateSources.ncm = funcref#Function('cm#snippet#_snipmate_snippets')
endfunc

func! cm#snippet#_snipmate_snippets(scopes, trigger, result)
	if empty(v:completed_item) || get(v:completed_item, 'snippet', '') == ''
		return
	endif
    " use version 1 snippet syntax
	let a:result[v:completed_item.snippet_word] = {'default': [v:completed_item.snippet, 1] }
endfunc

