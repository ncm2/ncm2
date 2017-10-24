
func! cm#sources#css#init()
    call cm#register_source({'name' : 'cm-css',
                \ 'priority': 9, 
                \ 'scoping': 1,
                \ 'scopes': ['css','scss'],
                \ 'abbreviation': 'css',
                \ 'word_pattern': '[\w\-]+',
                \ 'cm_refresh_patterns':['[\w\-]+\s*:\s+'],
                \ 'cm_refresh': {'omnifunc': 'csscomplete#CompleteCSS'},
                \ })
endfunc

