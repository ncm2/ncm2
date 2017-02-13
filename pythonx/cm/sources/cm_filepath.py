# -*- coding: utf-8 -*-

# For debugging, use this command to start neovim:
#
# NVIM_PYTHON_LOG_FILE=nvim.log NVIM_PYTHON_LOG_LEVEL=INFO nvim
#
#
# Please register source before executing any other code, this allow cm_core to
# read basic information about the source without loading the whole module, and
# modules required by this module
from cm import cm
cm.register_source(name='cm-filepath',
                   abbreviation='path',
                   cm_refresh_patterns=['[0-9a-zA-Z_\-\.\/~\$]{4,}$','\.\/[0-9a-zA-Z_\-\.\/~\$]*$'],
                   priority=6,
                   detach=1)

import os
import re
import logging
from neovim.api import Nvim

logger = logging.getLogger(__name__)

class Source:

    def __init__(self,nvim):

        """
        @type nvim: Nvim
        """

        self._nvim = nvim

        self._name_kw_pattern = r'[0-9a-zA-Z_\-\.]'
        self._path_kw_pattern = r'[0-9a-zA-Z_\-\.\/~\$]'

    def cm_refresh(self,info,ctx):

        lnum = ctx['lnum']
        col = ctx['col']
        typed = ctx['typed']
        filepath = ctx['filepath']

        # Note:
        # 
        # If you'r implementing you own source, and you want to get the content
        # of the file, Please use `cm.get_src()` instead of
        # `"\n".join(self._nvim.current.buffer[:])`
 
        pkw = re.search(self._path_kw_pattern+r'*?$',typed).group(0)
        nkw = re.search(self._name_kw_pattern+r'*?$',typed).group(0)
        startcol = col-len(nkw)

        dir = os.path.dirname(pkw)
        dir = os.path.expandvars(dir)
        dir = os.path.expanduser(dir)
        if dir=='' and len(nkw)<2:
            return

        # full path of current file, current working dir
        cwd = self._nvim.call('getcwd')
        curdir = os.path.dirname(filepath)

        bdirs = [ curdir, cwd]
        if pkw != './':
            bdirs.append('/')

        files = []
        for bdir in bdirs:
            joined_dir = os.path.join(bdir,dir.strip('/'))
            try:
                names = os.listdir(joined_dir)
                for name in names:
                    files.append(os.path.join(joined_dir,name))
            except Exception as ex:
                logger.info('exception on listing joined_dir [%s], %s', joined_dir, ex)
                continue

        # remove duplicate
        files = list(set(files))

        matches = []
        for file in files:
            word = os.path.basename(file)
            menu = file
            matches.append(dict(word=word,icase=1,menu=menu,dup=1))

        # simply limit the number of matches here, not to explode neovim
        matches = matches[0:1024]

        # cm#complete(src, context, startcol, matches)
        self._nvim.call('cm#complete', info['name'], ctx, startcol, matches, async=True)

