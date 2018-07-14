## Introduction

NCM2, formerly known as
[nvim-completion-manager](https://github.com/roxma/nvim-completion-manager),
is a slim, fast hackable completion framework, for neovim.

Main features:

1. Fast and asynchronous completion support, with vimscript friendly API.
2. Smart on files with different languages, for example, css/javascript
   completion in html style/script tag.
3. Function parameter expansion support using ncm2-plugin.

Read [our wiki page](https://github.com/ncm2/ncm2/wiki) for a list of
extensions and languages support for ncm2.

## Requirements

- `:echo has("nvim-0.2.2")` prints 1. Older versions has not been tested
- `:echo has("python3")` prints 1
- Plugin [nvim-yarp](https://github.com/roxma/nvim-yarp)

For vim8 user, read the [nvim-yarp](https://github.com/roxma/nvim-yarp)
README. Note that vim8 support is simply a bonus. It's not the goal of ncm2.

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

## By Me A Coffee.

This project is always gonna be FOSS. While it still takes me [lots of
effert](https://github.com/ncm2) to create & tune things amazing.

Feel free to buy me a coffe if you love this project.

Send [to roxma with paypal](https://www.paypal.me/roxma)

Or send to roxma with WeChat:

![WeChat Pay](https://user-images.githubusercontent.com/4538941/42722403-edfffb9a-877d-11e8-9fd9-615aeba0c3dd.png)
