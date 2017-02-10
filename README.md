 :heart: for my favorite editor

# A Completion Framework for Neovim

This is a **Fast! Extensible! Async! completion framework** for
[neovim](https://github.com/neovim/neovim).  For more information about plugin
implementation, please read the **[Why](#why) section**.

Future updates, announcements, screenshots will be posted
**[here](https://github.com/roxma/nvim-completion-manager/issues/12).
Subscribe it if you are interested.**

![All in one screenshot](https://cloud.githubusercontent.com/assets/4538941/22727187/78f35172-ee12-11e6-95e5-e9c160151f3b.gif)

## Table of Contents

<!-- vim-markdown-toc GFM -->
* [Available Completion Sources](#available-completion-sources)
* [Requirements](#requirements)
* [Installation](#installation)
* [Configuration Tips](#configuration-tips)
* [How to extend this framework?](#how-to-extend-this-framework)
* [Why?](#why)
    * [Async architecture](#async-architecture)
    * [Scoping](#scoping)
    * [Experimental hacking](#experimental-hacking)
* [FAQ](#faq)
    * [Vim 8 support?](#vim-8-support)
    * [Why Python?](#why-python)
* [Related Projects](#related-projects)

<!-- vim-markdown-toc -->

## Available Completion Sources

plugin builtin sources:

- Keyword from current buffer
- Tag completion. (`:help 'tags'`, `:help tagfiles()`)
- Keyword from tmux session
- Ultisnips hint
- File path completion
- Python code completion
- Javascript code completion
- Golang code completion

scoping features:

- Language specific completion for markdown
- Javascript code completion in html script tag
- Css code completion in html style tag

extra sources:

- [PHP code completion](https://github.com/roxma/nvim-cm-php-language-server)
  (experimental plugin for [language server
  ](https://github.com/neovim/neovim/issues/5522 support))


## Requirements

1. Neovim python3 support. `:help provider-python`. For lazy linux users, I
   recommend this plugin
   [python-support.nvim](https://github.com/roxma/python-support.nvim).
   (Note: Self promotion)
- For **python code completion**, you need to install
  [jedi](https://github.com/davidhalter/jedi) library. For python code
  completion in markdown file, you need to install
  [mistune](https://github.com/lepture/mistune)
- For **Javascript code completion**, you need to install nodejs and npm on your
  system.
- For **Golang code completion**, you need to install
  [gocode](https://github.com/nsf/gocode#setup).

## Installation

- Assumming you're using [vim-plug](https://github.com/junegunn/vim-plug)

```vim
" `npm install` For javascript code completion support
Plug 'roxma/nvim-completion-manager', {'do': 'npm install'}
" PHP code completion is moved to a standalone plugin
Plug 'roxma/nvim-cm-php-language-server',  {'do': 'composer install && composer run-script parse-stubs'}
```

- Install the required pip modules for you neovim python3:

```sh
pip3 --user install neovim jedi mistune psutil setproctitle
```

(Optional) It's easier to use
[python-support.nvim](/roxma/python-support.nvim) to help manage your pip
modules for neovim:

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

## Configuration Tips

- Supress the annoying completion messages:

```vim
" don't give |ins-completion-menu| messages.  For example,
" '-- XXX completion (YYY)', 'match 1 of 2', 'The only match',
set shortmess+=c
```

- **Tab Completion**

```vim
inoremap <expr> <Tab> pumvisible() ? "\<C-n>" : "\<Tab>"
inoremap <expr> <S-Tab> pumvisible() ? "\<C-p>" : "\<S-Tab>"
```

- Trigger Ultisnips or show popup hints [with the same
  key](https://github.com/roxma/nvim-completion-manager/issues/12#issuecomment-278605326)
  `<c-u>`

```vim
let g:UltiSnipsExpandTrigger = "<Plug>(ultisnips_expand)"
inoremap <silent> <c-u> <c-r>=cm#sources#ultisnips#trigger_or_popup("\<Plug>(ultisnips_expand)")<cr>
```

- There's no guarantee that this plugin will be compatible with other
  completion plugin in the same buffer. Use `let g:cm_enable_for_all=0` and
  `call cm#enable_for_buffer()` to use this plugin for specific buffer.

- To disable the tag completion source. It's also possible to use
  `g:cm#sources_override` to override other options of a completion source.

```vim
let g:cm#sources_override = {
    \ 'cm-tags': {'enable':0}
    \ }
```

## How to extend this framework?

- For really simple, light weight completion candidate calculation, refer to
  [autoload/cm/sources/ultisnips.vim](autoload/cm/sources/ultisnips.vim)
- For really async completion source (strongly encoraged), refer to the file
  path completion example:
  [autoload/cm/sources/cm_filepath.py](autoload/cm/sources/cm_filepath.py)
- For existing omni completion (strongly discoraged), refer to
  [this](https://github.com/roxma/nvim-completion-manager/issues/9#issuecomment-278895791)

Please upload your screenshot
[here](https://github.com/roxma/nvim-completion-manager/issues/12) after you
created the extension.


## Why?

I'm writing this for fun, feeding my own need, and it's working pleasingly for
me now. And It seems there's lots of differences between deoplete, YCM, and
nvim-completion-manager, by design.

I havn't read the source of YCM yet. So here I'm describing the main design of
NCM (from now on, I'm using NCM as short for nvim-completion-manager) and some
of the differences between deoplete and this plugin.

### Async architecture

Each completion source should be a standalone process, the manager notifies
the completion source for any text changing, even when popup menu is visible.
The completion source notifies the manager if there's any complete matches
available. After some basic priority sorting between completion sources, and
some simple filtering, the completion popup menu will be trigger with the
`complete()` function by the completion manager.

If some of the completion source is calculating matches for a long long time,
the popup menu will still be shown quickly if other completion sources works
properly. And if the user havn't changed anything, the popup menu will be
updated after the slow completion source finish the work.

As the time as of this plugin being created, the completion sources of
deoplete are gathered with `gather_candidates()` of the `Source` object,
inside a for loop, in deoplete's process. A slow completion source may defer
the display of popup menu. Of course It will not block the ui.

IMHO, NCM is potentially faster 'cause all completion sources run in parallel.

### Scoping

I write markdown file with code blocks quite often, so I've also implemented
[language specific completion for markdown
file](#language-specific-completion-for-markdown). This is a framework
feature, which is called scoping. It should work for any markdown code block
whose language completion source is avaible to NCM. I've also added support
for javascript completion in script tag of html files, and css completion in
style tag.

The idea was originated in
[vim-syntax-compl-pop](https://github.com/roxma/vim-syntax-compl-pop). Since
it's pure vimscript implementation, and there're some limitation currently
with neovim's syntax api. It's very likely that vim-syntax-compl-pop doesn't
work, for example, javascript completion in markdown or html script tag.  So I
use custom parser in NCM to implement the scoping features.

### Experimental hacking

Note that there's some hacking done in NCM. It uses a per 30ms timer to detect
changes even popup menu is visible, instead of using the `TextChangedI` event,
which only triggers when no popup menu is visible. This is important for
implementing the async architecture. I'm hoping one day neovim will offer
better option rather than a timer or the limited `TextChangedI`.

Deoplete and YCM are mature, they have tons of features I'm not offering
currently, which should be considered a main difference too.

## FAQ

### Vim 8 support?

Currently not available. Refer to
[#14](https://github.com/roxma/nvim-completion-manager/issues/14) for
discussion.

### Why Python?

YouCompleteMe has [good
explanation](https://github.com/Valloric/YouCompleteMe#why-isnt-ycm-just-written-in-plain-vimscript-ffs).

## Related Projects

[asyncomplete.vim](https://github.com/prabirshrestha/asyncomplete.vim)

