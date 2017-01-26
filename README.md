 :heart: for my favorite editor

# A Completion Framework for Neovim

This is my experimental completion framework for neovim, which offers great
flexibility for writing your own completion plugin, including async support.

## Requirements

1. Neovim python3 support. `:help provider-python`. For lazy linux users, I
  recommend this plugin
  [python-support.nvim](https://github.com/roxma/python-support.nvim).
  (Note: Self promotion)
- For python code completion, you need to install
  [jedi](https://github.com/davidhalter/jedi) library. For python code
  completion in markdown file, you need to install
  [mistune](https://github.com/lepture/mistune)


## Installation and Configuration

Assumming you're using [vim-plug](https://github.com/junegunn/vim-plug)

```vim
Plug 'roxma/nvim-complete-manager'
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

## How to extend this framework?

- For really simple, light weight completion candidate calculation, refer to
  [autoload/cm/sources/ultisnips.vim](autoload/cm/sources/ultisnips.vim)
- For really async completion source, refer to the buffer keyword example:
  [autoload/cm/sources/bufkeyword.py](autoload/cm/sources/bufkeyword.py)


## Demo

Keyword completion demo:

[![asciicast](https://asciinema.org/a/7kb5ihp73jvk8vytdjghwyu4t.png)](https://asciinema.org/a/7kb5ihp73jvk8vytdjghwyu4t)

Python completion demo:

[![asciicast](https://asciinema.org/a/5esfmuse51cfouikm7ik75hqo.png)](https://asciinema.org/a/5esfmuse51cfouikm7ik75hqo)

I also added python completion for markdown file, just for fun:

[![asciicast](https://asciinema.org/a/87jrqlcg3r8qyijcuo3pazcmc.png)](https://asciinema.org/a/87jrqlcg3r8qyijcuo3pazcmc)

## Why?

I'm writing this for fun, feeds my own need, and it's working pleasingly for
me now. And It seems there's lots of differences between deoplete, YCM, and
nvim-complete-manager, by design.

--- TO BE CONTINUED ---

