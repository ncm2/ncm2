
# Complete Manager for neovim 

This is my experimental completion framework for neovim.

I'm not gonna compete with deoplete or YCM. I'm writting this for fun, and they
are different in plugin design.

This plugin offers great flexibility for writing your own completion source
(async support).

There's no guarantee that this plugin will be compatible with other completion
plugin in the same buffer. Use `let g:cm_enable_for_all=0` and `call
cm#enable_for_buffer()` to use this plugin for specific buffer.


## requirement

The complete manager core itself is pure vimscript currently and has no
requirements. While the completion sources provided by this plugin need some
extra functionality to work.

- [nvim-possible-textchangedi](https://github.com/roxma/nvim-possible-textchangedi)

## How to extend this framework?

see [autoload/cm/sources/ultisnips.vim](autoload/cm/sources/ultisnips.vim)

