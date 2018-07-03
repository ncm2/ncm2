A slim, fast and hackable completion framework for
[neovim](https://github.com/neovim/neovim) :heart:

Formerly known as
[nvim-completion-manager](https://github.com/roxma/nvim-completion-manager).

Check the [ncm2-plugin topic](https://github.com/topics/ncm2-plugin) for a
list of plugins.

## Requirements

- `:echo has("nvim-0.2.2")` prints 1. Older versions has not been tested
- `:echo has("python3")` prints 1
- Plugin [nvim-yarp](https://github.com/roxma/nvim-yarp)

## Install

```vim
" assuming your using vim-plug: https://github.com/junegunn/vim-plug
Plug 'ncm2/ncm2'
" ncm2 requires nvim-yarp
Plug 'roxma/nvim-yarp'

" enable ncm2 for all buffer
autocmd BufEnter * call ncm2#enable_for_buffer()

" note that must keep noinsert in completeopt, the others is optional
set completeopt=noinsert,menuone,noselect
```

## Optional vimrc tips

```vim
" supress the annoying 'match x of y', 'The only match' messages
set shortmess+=c

" CTRL-C doesn't trigger the InsertLeave autocmd . map to <ESC> instead.
inoremap <c-c> <ESC>

" When the <Enter> key is pressed while the popup menu is visible, it only
" hides the menu. Use this mapping to close the menu and also start a new
" line.
inoremap <expr> <CR> (pumvisible() ? "\<c-y>\<cr>" : "\<CR>")

" Use <TAB> to select the popup menu:
inoremap <expr> <Tab> pumvisible() ? "\<C-n>" : "\<Tab>"
inoremap <expr> <S-Tab> pumvisible() ? "\<C-p>" : "\<S-Tab>"

" trigger completion on <backspace> and <c-w>
imap <backspace> <backspace><Plug>(ncm2_auto_trigger)
imap <c-w> <c-w><Plug>(ncm2_auto_trigger)

" wrap existing omnifunc
" Note that omnifunc does not run in background and may probably block the
" editor. If you don't want to be blocked by omnifunc too often, you could add
" 180ms delay before the omni wrapper:
"  'on_complete': ['ncm2#on_complete#delay', 180,
"               \ 'ncm2#on_complete#omni', 'csscomplete#CompleteCSS'],
au User Ncm2Plugin call ncm2#register_source({
        \ 'name' : 'css',
        \ 'priority': 9, 
        \ 'subscope_enable': 1,
        \ 'scope': ['css','scss'],
        \ 'mark': 'css',
        \ 'word_pattern': '[\w\-]+',
        \ 'complete_pattern': ':\s*',
        \ 'on_complete': ['ncm2#on_complete#omni', 'csscomplete#CompleteCSS'],
        \ })
```

## Completion Source

```vim
Plug 'ncm2/ncm2-bufword'
Plug 'ncm2/ncm2-tmux'
Plug 'ncm2/ncm2-path'
Plug 'ncm2/ncm2-jedi'
```

Check the [ncm2-source](https://github.com/topics/ncm2-source)  topic for more
information.

## Snippet Integration

- [ncm2-snipmate](https://github.com/ncm2/ncm2-snipmate)

Check the [ncm2-snippet](https://github.com/topics/ncm2-snippet) topic for
more information.

## Subscope

Example of enabling css/javascript completion in html file:

```vim
Plug 'ncm2/ncm2-html-subscope'
```

Check the [ncm2-subscope topic](https://github.com/topics/ncm2-subscope) for
more information.
