 :heart: for my favorite editor

# A Completion Framework for Neovim

This is a **fast, extensible, async completion framework** for
[neovim](https://github.com/neovim/neovim).  For more information about plugin
implementation, please read the **[Why](#why) section**.

Future updates, announcements, screenshots will be posted
**[here](https://github.com/roxma/nvim-completion-manager/issues/12).
Subscribe it if you are interested.**

![All in one screenshot](https://cloud.githubusercontent.com/assets/4538941/23752974/8fffbdda-0512-11e7-8466-8a30f480de21.gif)


## Table of Contents

<!-- vim-markdown-toc GFM -->
* [Features](#features)
* [Scoping Sources:](#scoping-sources)
* [Completion Sources](#completion-sources)
* [How to extend this framework?](#how-to-extend-this-framework)
* [Requirements](#requirements)
* [Installation](#installation)
* [Optional Configuration Tips](#optional-configuration-tips)
* [Why?](#why)
    * [Async architecture](#async-architecture)
    * [Scoping](#scoping)
    * [Experimental hacking](#experimental-hacking)
* [FAQ](#faq)
    * [Why Python?](#why-python)
* [Trouble-shooting](#trouble-shooting)
* [Related Projects](#related-projects)

<!-- vim-markdown-toc -->


## Features

1. Asynchronous completion support like deoplete.
2. Faster, all completions should run in parallel.
3. Smarter on files with different languages, for example, css/javascript
completion in html style/script tag.
4. Extensible async vimscript API and python3 API.
5. Function parameter expansion via
   [Ultisnips](https://github.com/SirVer/ultisnips),
   [neosnippet.vim](https://github.com/Shougo/neosnippet.vim) or
   [vim-snipmate](https://github.com/garbas/vim-snipmate).


## Scoping Sources:

- Language specific completion for markdown
- Javascript code completion in html script tag
- Css code completion in html style tag

## Completion Sources

| Language / Description   | Repository                                                                             |
|--------------------------|----------------------------------------------------------------------------------------|
| Word from current buffer | builtin                                                                                |
| Word from tmux session   | builtin                                                                                |
| ctags completion         | builtin                                                                                |
| Filepath completion      | builtin                                                                                |
| Python                   | builtin, requires [jedi](https://github.com/davidhalter/jedi)                          |
| Css                      | builtin, requires [csscomplete#CompleteCSS](https://github.com/othree/csscomplete.vim) |
| Golang                   | builtin, requires [gocode](https://github.com/nsf/gocode)                              |
| Ultisnips hint           | builtin, requires [Ultisnips](https://github.com/SirVer/ultisnips)                     |
| Snipmate hint            | builtin, requires [vim-snipmate](https://github.com/garbas/vim-snipmate)               |
| neosnippet hint          | builtin, requires [neosnippet.vim](https://github.com/Shougo/neosnippet.vim)           |
| Language Server Protocal | [LanguageClient-neovim](https://github.com/autozimu/LanguageClient-neovim)             |
| C/C++                    | [clang_complete](https://github.com/roxma/clang_complete)                              |
| Javascript               | [nvim-cm-tern](https://github.com/roxma/nvim-cm-tern)                                  |
| Javascript               | [nvim-cm-flow](https://github.com/roxma/ncm-flow)                                      |
| elm                      | [ncm-elm-oracle](https://github.com/roxma/ncm-elm-oracle)                              |
| Clojure                  | [async-clj-omni](https://github.com/clojure-vim/async-clj-omni)                        |
| Rust                     | [nvim-cm-racer](https://github.com/roxma/nvim-cm-racer)                                |
| Vimscript                | [neco-vim](https://github.com/Shougo/neco-vim)                                         |
| Ruby                     | [ncm-rct-complete](https://github.com/roxma/ncm-rct-complete)                          |
| PHP                      | [LanguageServer-php-neovim](https://github.com/roxma/LanguageServer-php-neovim)        |
| Swift                    | [nvim-cm-swift-completer](https://github.com/dafufer/nvim-cm-swift-completer)          |
| gtags completion         | [gen_tags.vim](https://github.com/jsfaint/gen_tags.vim)                                |
| syntax completion        | [neco-syntax](https://github.com/Shougo/neco-syntax)                                   |
| include completion       | [neoinclude](https://github.com/Shougo/neoinclude.vim)                                 |
| github completion        | [ncm-github](https://github.com/roxma/ncm-github)                                      |
| mutt mails               | [#97 mutt-aliases.vim](https://github.com/roxma/nvim-completion-manager/issues/97)     |
| deoplete                 | [#50 deoplete](https://github.com/roxma/nvim-completion-manager/issues/50)             |
| css                      | [ncm-css](https://github.com/calebeby/ncm-css)                                         |
| lbdb (addressbook)       | [ncm-lbdb](https://github.com/katsika/ncm-lbdb)                                        |


## How to extend this framework?

- `:help ncm-source-examples` for minimal examples
- Some real, small examples:
  [github-emoji](https://github.com/roxma/ncm-github/blob/master/pythonx/cm_sources/github_emoji.py),
  [nvim-cm-racer](https://github.com/roxma/nvim-cm-racer)

Please upload your new plugin, or possibly screenshot
[here](https://github.com/roxma/nvim-completion-manager/issues/12) after you
created the extension.


## Requirements

- `has("python3")`.
- If you're on vim8, [vim-hug-neovim-rpc](https://github.com/roxma/vim-hug-neovim-rpc).

## Installation

- Assuming you're using [vim-plug](https://github.com/junegunn/vim-plug)

```vim
" the framework
Plug 'roxma/nvim-completion-manager'
```

- If you are **vim8 user**, you'll need
  [vim-hug-neovim-rpc](https://github.com/roxma/vim-hug-neovim-rpc). The vim8
  support layer is still experimental, please 'upgrade' to
  [neovim](https://github.com/neovim/neovim) if it's possible.

```vim
" Requires vim8 with has('python') or has('python3')
" Requires the installation of msgpack-python. (pip install msgpack-python)
if !has('nvim')
    Plug 'roxma/vim-hug-neovim-rpc'
endif
```

- Install pip modules for your neovim python3:

```sh
# neovim is the required pip module
# jedi for python completion
# mistune for markdown completion (optional)
# psutil (optional)
# setproctitle (optional)
pip3 install --user neovim jedi mistune psutil setproctitle
```

(Optional) It's easier to use
[python-support.nvim](https://github.com/roxma/python-support.nvim) to help
manage your pip modules for neovim:

```vim
Plug 'roxma/python-support.nvim'
" for python completions
let g:python_support_python3_requirements = add(get(g:,'python_support_python3_requirements',[]),'jedi')
" language specific completions on markdown file
let g:python_support_python3_requirements = add(get(g:,'python_support_python3_requirements',[]),'mistune')

" utils, optional
let g:python_support_python3_requirements = add(get(g:,'python_support_python3_requirements',[]),'psutil')
let g:python_support_python3_requirements = add(get(g:,'python_support_python3_requirements',[]),'setproctitle')

```

- (Optional) Install typical completion sources
```vim
" (optional) javascript completion
Plug 'roxma/nvim-cm-tern',  {'do': 'npm install'}
" (optional) language server protocol framework
Plug 'autozimu/LanguageClient-neovim', { 'do': ':UpdateRemotePlugins' }
" (optional) php completion via LanguageClient-neovim
Plug 'roxma/LanguageServer-php-neovim',  {'do': 'composer install && composer run-script parse-stubs'}
autocmd FileType php LanguageClientStart
```

## Optional Configuration Tips

- Supress the annoying completion messages:

```vim
" don't give |ins-completion-menu| messages.  For example,
" '-- XXX completion (YYY)', 'match 1 of 2', 'The only match',
set shortmess+=c
```

- When the  `<Enter>` key is pressed while the popup menu is visible, it only
  hides the menu. Use this mapping to hide the menu and also start a new line.

```vim
inoremap <expr> <CR> (pumvisible() ? "\<c-y>\<cr>" : "\<CR>")
```

- When using `CTRL-C` key to leave insert mode, it does not trigger the
  autocmd `InsertLeave`. You should use `CTRL-[`, or map the `<c-c>` to
  `<ESC>`.

```vim
inoremap <c-c> <ESC>
```

- Use `<TAB>` to select the popup menu:

```vim
inoremap <expr> <Tab> pumvisible() ? "\<C-n>" : "\<Tab>"
inoremap <expr> <S-Tab> pumvisible() ? "\<C-p>" : "\<S-Tab>"
```

- If 'omnifunc' is the only available option, you may register it as a source
  for NCM.
 
 
```vim
" css completion via `csscomplete#CompleteCSS`
" The `'cm_refresh_patterns'` is PCRE.
" Be careful with `'scoping': 1` here, not all sources, especially omnifunc,
" can handle this feature properly.
au User CmSetup call cm#register_source({'name' : 'cm-css',
        \ 'priority': 9, 
        \ 'scoping': 1,
        \ 'scopes': ['css','scss'],
        \ 'abbreviation': 'css',
        \ 'word_pattern': '[\w\-]+',
        \ 'cm_refresh_patterns':['[\w\-]+\s*:\s+'],
        \ 'cm_refresh': {'omnifunc': 'csscomplete#CompleteCSS'},
        \ })
```

**Warning:** `omnifunc` is implemented in a synchronouse style, and
vim-vimscript is single threaded, it would potentially block the ui with the
introduction of a heavy weight `omnifunc`, for example the builtin
phpcomplete. If you get some time, please try implementing a source for NCM as
a replacement for the old style omnifunc.


- There's no guarantee that this plugin will be compatible with other
  completion plugin in the same buffer. Use `let g:cm_smart_enable=0` and
  `call cm#enable_for_buffer()` to use this plugin for specific buffer.

- This example shows how to disable NCM's builtin tag completion. It's also
  possible to use `g:cm_sources_override` to override other default options of
  a completion source.

```vim
let g:cm_sources_override = {
    \ 'cm-tags': {'enable':0}
    \ }
```

## Why?

This project was started just for fun, and it's working pleasingly for me now.
However, it seems there's lots of differences between deoplete, YCM, and
nvim-completion-manager, by implementation.

I haven't read the source of YCM yet. So here I'm describing the basic
implementation of NCM (short for nvim-completion-manager) and some of the
differences between deoplete and this plugin.

### Async architecture

Each completion source should be a thread or a standalone process, the manager
notifies the completion source for any text changing, even when popup menu is
visible.  The completion source notifies the manager if there's any complete
matches available. After some basic priority sorting between completion
sources, and some simple filtering, the completion popup menu will be
triggered with the `complete()` function by the completion manager.

If some of the completion source is calculating matches for a long long time,
the popup menu will still be shown quickly if other completion sources work
properly. And if the user hasn't changed anything, the popup menu will be
updated after the slow completion source finishes the work.

As the time as of this plugin being created, the completion sources of
deoplete are gathered with `gather_candidates()` of the `Source` object,
inside a for loop, in deoplete's process. A slow completion source may defer
the display of popup menu. Of course it will not block the ui.

The good news is that deoplete has supported async `gather_candidates` now.
But still, NCM is potentially faster because all completion sources run in
parallel.

### Scoping

I write markdown files with code blocks quite often, so I've also implemented
language specific completion for markdown file. This is a framework feature,
which is called scoping. It should work for any markdown code block whose
language completion source is avaible to NCM. I've also added support for
javascript completion in script tag of html files, and css completion in style
tag.

The idea was originated in
[vim-syntax-compl-pop](https://github.com/roxma/vim-syntax-compl-pop). Since
it's pure vimscript implementation, and there are some limitations currently
with neovim's syntax api. It's very likely that vim-syntax-compl-pop doesn't
work, for example, javascript completion in markdown or html script tag.  So I
use custom parser in NCM to implement the scoping features.

### Experimental hacking

Note that there's some hacking done in NCM. It uses a per 30ms timer to detect
changes even popup menu is visible, as well as using the `TextChangedI` event,
which only triggers when no popup menu is visible. This is important for
implementing the async architecture. I'm hoping one day neovim will offer
better option rather than a timer or the limited `TextChangedI`.

## FAQ

### Why Python?

YouCompleteMe has [good
explanation](https://github.com/Valloric/YouCompleteMe#why-isnt-ycm-just-written-in-plain-vimscript-ffs).

## Trouble-shooting

Moved to [wiki](https://github.com/roxma/nvim-completion-manager/wiki/Trouble-shooting)

## Related Projects

[asyncomplete.vim](https://github.com/prabirshrestha/asyncomplete.vim)

