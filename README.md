A fast, slim completion framework for
[neovim](https://github.com/neovim/neovim) :heart:

Check the [ncm2-plugin topic](https://github.com/topics/ncm2-plugin) for a
list of plugins.

## Requirements

- `:echo has("nvim-0.2.2")` prints 1. Older versions has not been tested
- `:echo has("python3")` prints 1
- Plugin [nvim-yarp](https://github.com/roxma/nvim-yarp)

## Usage

Here is a basic vimrc example:

```vim
" assuming your using vim-plug: https://github.com/junegunn/vim-plug
Plug 'ncm2/ncm2'
" ncm2 requires nvim-yarp
Plug 'ncm2/nvim-yarp'

" enable ncm2 for all buffer
autocmd BufEnter * call ncm2#enable_for_buffer()

" note that must keep noinsert in completeopt, the others is optional
set completeopt=noinsert,menuone,noselect

" ### The following vimrc is optional

" supress the annoying 'match x of y', 'The only match' messages
set shortmess+=c

" when using CTRL-C key to leave insert mode, it does not trigger the autocmd
" InsertLeave. You should use CTRL-[, or map the <c-c> to <ESC>.
inoremap <c-c> <ESC>

" When the <Enter> key is pressed while the popup menu is visible, it only
" hides the menu. Use this mapping to hide the menu and also start a new line.
inoremap <expr> <CR> (pumvisible() ? "\<c-y>\<cr>" : "\<CR>")

" Use <TAB> to select the popup menu:
inoremap <expr> <Tab> pumvisible() ? "\<C-n>" : "\<Tab>"
inoremap <expr> <S-Tab> pumvisible() ? "\<C-p>" : "\<S-Tab>"

" ncm2 plugins
Plug 'ncm2/nvim-bufword'
Plug 'ncm2/nvim-tmux'
```
