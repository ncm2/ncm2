
call feedkeys('Goab')

try
	PasteEasyDisable
catch
endtry

let g:cm_sources = ['']
let b:cm_enable = 1

augroup foo
	autocmd!
	autocmd CursorMovedI * call s:foo()
augroup end

func! s:foo()

	if col('.')!=3
		return
	endif

	call cm#register_source({'name':'cm-buffer-keyword', 'priority': 4, 'abbreviation': 'bword'})
	call cm#register_source({'name':'cm-buffer-keyword2', 'priority': 5, 'abbreviation': 'bword2'})
	call cm#register_source({'name':'cm-buffer-keyword3', 'priority': 6, 'abbreviation': 'bword3'})
	call cm#complete('cm-buffer-keyword', cm#context(), 1, ['abchkj'])
	call cm#complete('cm-buffer-keyword2', cm#context(), 2, [ { 'word':'bcef'} ])
	call cm#complete('cm-buffer-keyword3', cm#context(), 2, [ { 'word':'bcef'} ])

endfunc
