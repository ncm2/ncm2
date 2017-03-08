# -*- coding: utf-8 -*-

# For debugging, use this command to start neovim:
#
# NVIM_PYTHON_LOG_FILE=nvim.log NVIM_PYTHON_LOG_LEVEL=INFO nvim
#
#
# Please register source before executing any other code, this allow cm_core to
# read basic information about the source without loading the whole module, and
# modules required by this module
from cm import register_source, getLogger, Base
register_source(name='cm-filepath',
                abbreviation='path',
                word_pattern=r'[^\s,\\\/]+',
                cm_refresh_patterns=[r'(\.[\/\\]|[a-zA-Z]:\\|~\/)[0-9a-zA-Z_\-\.\\\/~\$]*$'],
                options=dict(path_pattern=r'[^\s,]+'),
                priority=6,)

import os
import re
from neovim.api import Nvim

class Source(Base):

    def __init__(self,nvim):
        super(Source,self).__init__(nvim)

    def cm_refresh(self,info,ctx):

        typed = ctx['typed']
        filepath = ctx['filepath']
        startcol = ctx['startcol']

        pkw = re.search(info['options']['path_pattern']+r'$',typed).group(0)

        dir = os.path.dirname(pkw)
        dir = os.path.expandvars(dir)
        dir = os.path.expanduser(dir)

        self.logger.debug('dir: %s', dir)

        # full path of current file, current working dir
        cwd = self.nvim.call('getcwd')
        curdir = os.path.dirname(filepath)

        bdirs = [curdir, cwd]
        if (pkw!="./") and (pkw!=".\\"):
            bdirs.append("/")

        files = []
        for bdir in bdirs:
            joined_dir = os.path.join(bdir,dir.strip('/'))
            self.logger.debug('searching dir: %s', joined_dir)
            try:
                names = os.listdir(joined_dir)
                self.logger.debug('search result: %s', names)
                for name in names:
                    files.append(os.path.join(joined_dir,name))
            except Exception as ex:
                self.logger.info('exception on listing joined_dir [%s], %s', joined_dir, ex)
                continue

        # remove duplicate
        files = list(set(files))

        matches = []
        for file in files:
            word = os.path.basename(file)
            menu = file
            matches.append(dict(word=word,icase=1,menu=menu,dup=1))

        # pre filtering
        matches = self.matcher.process(info, ctx, startcol, matches)
        refresh = 0
        if len(matches)>1024:
            refresh = 1
            matches = matches[0:1024]

        self.logger.debug('startcol: %s, matches: %s', startcol, matches)
        self.nvim.call('cm#complete', info['name'], ctx, startcol, matches, refresh, async=True)

