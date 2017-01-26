
# Complete Manager for My :heart: Favorite Editor 

This is my experimental completion framework for neovim, which offers great
flexibility for writing your own completion plugin, including async support.

## Requirements

1 Neovim python3 support. `:help provider-python`. For lazy linux users, I
  recommend this plugin
  [python-support.nvim](https://github.com/roxma/python-support.nvim).
  (Note: Self promotion)
- For python code completion, you need to install
  [jedi](https://github.com/davidhalter/jedi) library. For python code
  completion in markdown file, you need to install
  [mistune](https://github.com/lepture/mistune)

If you are using
[python-support.nvim](https://github.com/roxma/python-support.nvim), add the
following code into your vimrc, to satisfy requirement 1 and requirement 2.
(I asumming you'r using [vim-plug](https://github.com/junegunn/vim-plug)

```vim
Plug 'roxma/nvim-complete-manager'
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

