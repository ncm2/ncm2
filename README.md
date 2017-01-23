
# Complete Manager for neovim 

This is my experimental completion framework for neovim.

I'm not gonna compete with deoplete or YCM. I'm writting this for fun, and they
are different in plugin design.

This plugin offers great flexibility for writing your own completion source.


## requirement

The complete manager core itself is pure vimscript currently and has no
requirements. While the built-in completion sources provided by this plugin
need some extra functionality to work.

- [nvim-possible-textchangedi](https://github.com/roxma/nvim-possible-textchangedi)

## How to extend this framework?

see [autoload/cm/sources/ultisnips.vim](autoload/cm/sources/ultisnips.vim)

