# -*- coding: utf-8 -*-

# For debugging, use this command to start neovim:
#
# NVIM_PYTHON_LOG_FILE=nvim.log NVIM_PYTHON_LOG_LEVEL=INFO nvim
#
#
# Please register source before executing any other code, this allow cm_core to
# read basic information about the source without loading the whole module, and
# modules required by this module
from cm import register_source, get_matcher, getLogger
register_source(name='cm-filepath',
                abbreviation='path',
                word_pattern=r'[^\s,\\\/]+',
                cm_refresh_patterns=[r'(\.[\/\\]|[a-zA-Z]:\\|~\/)[0-9a-zA-Z_\-\.\\\/~\$]*$'],
                options=dict(path_pattern=r'[^\s,]+'),
                priority=6,)

import os
import re
from neovim.api import Nvim

logger = getLogger(__name__)

class Source:

    def __init__(self,nvim):

        """
        @type nvim: Nvim
        """

        self._nvim = nvim

    def cm_refresh(self,info,ctx):

        typed = ctx['typed']
        filepath = ctx['filepath']
        startcol = ctx['startcol']

        pkw = re.search(info['options']['path_pattern']+r'$',typed).group(0)

        dir = os.path.dirname(pkw)
        dir = os.path.expandvars(dir)
        dir = os.path.expanduser(dir)

        logger.debug('dir: %s', dir)

        # full path of current file, current working dir
        cwd = self._nvim.call('getcwd')
        curdir = os.path.dirname(filepath)

        bdirs = [curdir, cwd]
        if (pkw!="./") and (pkw!=".\\"):
            bdirs.append("/")

        files = []
        for bdir in bdirs:
            joined_dir = os.path.join(bdir,dir.strip('/'))
            logger.debug('searching dir: %s', joined_dir)
            try:
                names = os.listdir(joined_dir)
                logger.debug('search result: %s', names)
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

        # pre filtering
        matches = get_matcher(self._nvim).process(info, ctx, startcol, matches)
        refresh = 0
        if len(matches)>1024:
            refresh = 1
            matches = matches[0:1024]

        logger.debug('startcol: %s, matches: %s', startcol, matches)
        self._nvim.call('cm#complete', info['name'], ctx, startcol, matches, refresh, async=True)

