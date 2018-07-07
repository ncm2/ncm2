## Introduction

NCM2, formerly known as
[nvim-completion-manager](https://github.com/roxma/nvim-completion-manager),
is a slim, fast hackable completion framework, for neovim.

Main features:

1. Fast and asynchronous completion support, with vimscript friendly API.
2. Smart on files with different languages, for example, css/javascript
   completion in html style/script tag.
3. Function parameter expansion support using ncm2-plugin.

Here's a list of links where you can find extensions for ncm2.

- our [wiki](https://github.com/ncm2/ncm2/wiki) page
- [ncm2-plugin](https://github.com/topics/ncm2-plugin) github topic
- [ncm2-source](https://github.com/topics/ncm2-source) github topic
- [ncm2-subscope](https://github.com/topics/ncm2-subscope) github topic
- [ncm2-snippet](https://github.com/topics/ncm2-snippet) github topic
- [ncm2-utils](https://github.com/topics/ncm2-utils) github topic

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
    " supress the annoying 'match x of y', 'The only match' and 'Pattern not
    " found' messages
    set shortmess+=c

    " enable auto complete for `<backspace>`, `<c-w>` keys.
    " known issue https://github.com/ncm2/ncm2/issues/7
    au TextChangedI * call ncm2#auto_trigger()

    " CTRL-C doesn't trigger the InsertLeave autocmd . map to <ESC> instead.
    inoremap <c-c> <ESC>

    " When the <Enter> key is pressed while the popup menu is visible, it only
    " hides the menu. Use this mapping to close the menu and also start a new
    " line.
    inoremap <expr> <CR> (pumvisible() ? "\<c-y>\<cr>" : "\<CR>")

    " Use <TAB> to select the popup menu:
    inoremap <expr> <Tab> pumvisible() ? "\<C-n>" : "\<Tab>"
    inoremap <expr> <S-Tab> pumvisible() ? "\<C-p>" : "\<S-Tab>"

    " wrap existing omnifunc
    " Note that omnifunc does not run in background and may probably block the
    " editor. If you don't want to be blocked by omnifunc too often, you could
    " add 180ms delay before the omni wrapper:
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

    " some completion sources
    Plug 'ncm2/ncm2-bufword'
    Plug 'ncm2/ncm2-tmux'
    Plug 'ncm2/ncm2-path'
    Plug 'ncm2/ncm2-jedi'
```
