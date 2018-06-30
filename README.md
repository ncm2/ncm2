A fast, slim completion framework for
[neovim](https://github.com/neovim/neovim) :heart:

Check the [ncm2-plugin topic](https://github.com/topics/ncm2-plugin) for a
list of plugins.

## Requirements

- `:echo has("nvim-0.2.2")` prints 1. Older versions has not been tested.
- `:echo has("python3")` prints 1

## Usage

Here is a basic vimrc example:

```vim
" assuming your using vim-plug: https://github.com/junegunn/vim-plug
Plug 'ncm2/ncm2'
" ncm2 requires nvim-yarp
Plug 'ncm2/nvim-yarp'

" [Optional] completions from current buffer
Plug 'ncm2/nvim-bufword'

" enable ncm for all buffer
autocmd BufEnter * call ncm2#enable_for_buffer()

" note that must keep noinsert in completeopt, the others is optional
set completeopt=noinsert,menuone,noselect

" supress the annoying 'match x of y', 'The only match' messages
set shortmess+=c

" when using CTRL-C key to leave insert mode, it does not trigger the autocmd
" InsertLeave. You should use CTRL-[, or map the <c-c> to <ESC>.
" inoremap <c-c> <ESC>

" Use <TAB> to select the popup menu:
inoremap <expr> <Tab> pumvisible() ? "\<C-n>" : "\<Tab>"
inoremap <expr> <S-Tab> pumvisible() ? "\<C-p>" : "\<S-Tab>"
```
