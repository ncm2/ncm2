## Introduction

NCM2, formerly known as
[nvim-completion-manager](https://github.com/roxma/nvim-completion-manager),
is a slim, fast and hackable completion framework for neovim.

Main features:

1. Fast and asynchronous completion support, with vimscript friendly API.
2. Smart on files with different languages, for example, css/javascript
   completion in html style/script tag.
3. Function parameter expansion support using
   [ncm2-snippet](https://github.com/topics/ncm2-snippet) plugins.
4. [Language server protocol plugin
   integration](https://github.com/ncm2/ncm2/wiki).

Read [our wiki page](https://github.com/ncm2/ncm2/wiki) for a list of
extensions and programming languages support for NCM2.

![peek 2018-07-17 18-15](https://user-images.githubusercontent.com/4538941/42811661-dbfb5ba2-89ed-11e8-81c4-3fb893d1af9c.gif)

[View demo vimrc at #19](https://github.com/ncm2/ncm2/issues/19)

## Requirements

- `:echo has("nvim-0.2.2")` prints 1. Older versions has not been tested
- `:echo has("python3")` prints 1. This is usually set by
    `python3 -m pip install pynvim` in shell and
  `let g:python3_host_prog=/path/to/python/executable/` in vimrc.
- Plugin [nvim-yarp](https://github.com/roxma/nvim-yarp)

For vim8 user, read the [nvim-yarp](https://github.com/roxma/nvim-yarp)
README. **Note that vim8 support is simply a bonus. It's not the goal of
NCM2.**

## Install

```vim
    " assuming you're using vim-plug: https://github.com/junegunn/vim-plug
    Plug 'ncm2/ncm2'
    Plug 'roxma/nvim-yarp'

    " enable ncm2 for all buffers
    autocmd BufEnter * call ncm2#enable_for_buffer()

    " IMPORTANT: :help Ncm2PopupOpen for more information
    set completeopt=noinsert,menuone,noselect

    " NOTE: you need to install completion sources to get completions. Check
    " our wiki page for a list of sources: https://github.com/ncm2/ncm2/wiki
    Plug 'ncm2/ncm2-bufword'
    Plug 'ncm2/ncm2-path'
```

## Optional Vimrc Tips

```vim
    " suppress the annoying 'match x of y', 'The only match' and 'Pattern not
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
```

## How Do I write Ncm2 Source?

One important step is to understand how and when completion gets triggered.
Read `:help ncm2#register_source` carefully, or `:help
ncm2#register_source-example` for quick start.

In case you don't know what tool you should use for async support. Here are
some options available:

- `:help jobstart()`
- [python remote plugin
  example](https://github.com/jacobsimpson/nvim-example-python-plugin)
- I myself prefer to use [nvim-yarp](https://github.com/roxma/nvim-yarp)
    - Read [ncm2/ncm2-bufword](https://github.com/ncm2/ncm2-bufword) for
        example

## Debugging

Refer to the [debugging section of nvim-yarp](https://github.com/roxma/nvim-yarp#debugging)
