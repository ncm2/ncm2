
if get(g:,'cm_enable_for_all',1)
	" simple ignore files larger than 1M, for performance
	au BufWinEnter * if (exists('b:cm_enable')==0 && line2byte(line("$") + 1)<1000000) | call cm#enable_for_buffer() | endif
endif


