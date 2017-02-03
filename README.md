 :heart: for my favorite editor

# A Completion Framework for Neovim

This is my **experimental** completion framework for neovim, which offers
great flexibility for writing your own completion plugin, including async
support.

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

## Installation and Configuration

Assumming you're using [vim-plug](https://github.com/junegunn/vim-plug)

```vim
" `npm install` For javascript code completion support
Plug 'roxma/nvim-completion-manager', {'do': 'npm install'}
" PHP code completion is moved to a standalone plugin
Plug 'roxma/nvim-cm-php-language-server',  {'do': 'composer install && composer run-script parse-stubs'}
```

If you are using
[python-support.nvim](https://github.com/roxma/python-support.nvim), add the
following code into your vimrc, to satisfy requirement 1 and requirement 2.

```vim
Plug 'roxma/python-support.nvim'
" for python completions
let g:python_support_python3_requirements = add(get(g:,'python_support_python3_requirements',[]),'jedi')
" enable python completions on markdown file
let g:python_support_python3_requirements = add(get(g:,'python_support_python3_requirements',[]),'mistune')
```

Add this to supress the annoying completion messages:

```vim
" don't give |ins-completion-menu| messages.  For example,
" '-- XXX completion (YYY)', 'match 1 of 2', 'The only match',
set shortmess+=c
```

**Note** that there's no guarantee that this plugin will be compatible with
other completion plugin in the same buffer. Use `let g:cm_enable_for_all=0`
and `call cm#enable_for_buffer()` to use this plugin for specific buffer.

**Tab Completion**

```vim
inoremap <expr> <Tab> pumvisible() ? "\<C-n>" : "\<Tab>"
inoremap <expr> <S-Tab> pumvisible() ? "\<C-p>" : "\<S-Tab>"
```


## Current Completion Sources

- [Keyword from current buffer](#keyword-from-current-buffer)
- [Ultisnips hint](#ultisnips-hint)
- [File path completion](#file-path-completion)
- [Python code completion](#python-code-completion)
- [Javascript code completion](#javascript-code-completion)
- [Golang code completion](#golang-code-completion)
- [PHP code completion](https://github.com/roxma/nvim-cm-php-language-server)

## How to extend this framework?

- For really simple, light weight completion candidate calculation, refer to
  [autoload/cm/sources/ultisnips.vim](autoload/cm/sources/ultisnips.vim)
- For really async completion source, refer to the file path completion example:
  [autoload/cm/sources/cm_filepath.py](autoload/cm/sources/cm_filepath.py)


## Why?

I'm writing this for fun, feeding my own need, and it's working pleasingly for
me now. And It seems there's lots of differences between deoplete, YCM, and
nvim-completion-manager, by design.

I havn't read the source of YCM yet. So here I'm describing the main design of
NCM (from now on, I'm using NCM as short for nvim-completion-manager) and some
of the differences between deoplete and this plugin.

Each completion source should be a standalone process, the manager notifies
the completion source for any text changing, even when popup menu is visible.
The completion source notifies the manager if there's any complete matches
available. After some basic priority sorting between completion sources, and
some simple filtering, the completion popup menu will be trigger with the
`complete()` function by the completion manager.

As shown intentionally in the python jedi completion demo, If some of the
completion source is calculating matches for a long long time, the popup menu
will still be shown quickly if other completion sources works properly. And if
the user havn't changed anything, the popup menu will be updated later after
the slow completion source finish the work.

As the time as of this plugin being created, the completion sources of
deoplete are gathered with `gather_candidates()` of the `Source` object,
inside a for loop, in deoplete's process. A slow completion source may defer
the display of popup menu. Of course It will not block the ui.

There's some hacking done in NCM. It uses a per 30ms timer to detect changes
even popup menu is visible. NCM uses job_start function to start the
completion core process by itself, to illiminate the `:UpdateRemotePlugins`
command after installation, so that it should just work out of the box.

Note that the calling context of nvim's `complete()` function by NCM does not
meet the requirement in the documentation `:help complete()`, which says:

> You need to use a mapping with CTRL-R = |i_CTRL-R|.  It does not work after
> CTRL-O or with an expression mapping.

I work on remote VM quite often. I tend to avoid the `CTRL-R =` mapping,
because this triggers text updated on neovim's command line and it's
potentially slowing down the ui. Luckily it seems it's working by calling this
function directly. This is why I claimed **it's experimental**. I'm hoping one
day I can confirm that the calling context is legal.

Deoplete and YCM are mature, legit, they have tons of features I'm not
offering currently, which should be considered a main difference too.

## FAQ

### Vim 8 support?

Sorry, no plan for that. [#1](https://github.com/roxma/nvim-completion-manager/issues/1)

## Related Projects

[asyncomplete.vim](https://github.com/prabirshrestha/asyncomplete.vim)

## Demo

### Keyword from current buffer

[![asciicast buffer keyword completion](https://asciinema.org/a/7kb5ihp73jvk8vytdjghwyu4t.png)](https://asciinema.org/a/7kb5ihp73jvk8vytdjghwyu4t)

### Ultisnips hint

[![asciicast ultisnips hint completion](https://asciinema.org/a/3swl7vylxhjyg2yyd8vdu0tde.png)](https://asciinema.org/a/3swl7vylxhjyg2yyd8vdu0tde)

### File path completion

[![asciicast file path completion](https://asciinema.org/a/2me1ahjfahko8a1xnblls1k41.png)](https://asciinema.org/a/2me1ahjfahko8a1xnblls1k41)

### Python code completion

[![asciicast ppython completion](https://asciinema.org/a/5esfmuse51cfouikm7ik75hqo.png)](https://asciinema.org/a/5esfmuse51cfouikm7ik75hqo)

I also added python completion for markdown file, just for fun:

[![asciicast python markdown completion](https://asciinema.org/a/87jrqlcg3r8qyijcuo3pazcmc.png)](https://asciinema.org/a/87jrqlcg3r8qyijcuo3pazcmc)

### Javascript code completion

[![asciicast javascript code completion](https://asciinema.org/a/72m5ckw7k1m39kquro2jr0l1i.png)](https://asciinema.org/a/72m5ckw7k1m39kquro2jr0l1i)

### Golang code completion

[![asciicast golang code completion](https://asciinema.org/a/f45w82dwalitn5fyfpe29x3ua.png)](https://asciinema.org/a/f45w82dwalitn5fyfpe29x3ua)

