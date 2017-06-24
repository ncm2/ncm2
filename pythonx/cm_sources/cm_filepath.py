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
                word_pattern=r'''([^\W]|[-.~%$])+''',
                cm_refresh_patterns=[
                    r'''(\.[/\\]+|[a-zA-Z]:\\+|~\/+)''', r'''([^\W]|[-.~%$]|[/\\])+[/\\]+'''],
                options=dict(path_pattern=r'''(([^\W]|[-.~%$]|[/\\])+)'''),
                sort=0,
                priority=6,)

import os
import re
from neovim.api import Nvim


class Source(Base):

    def __init__(self, nvim):
        super(Source, self).__init__(nvim)

    def cm_refresh(self, info, ctx):

        typed = ctx['typed']
        filepath = ctx['filepath']
        startcol = ctx['startcol']

        pkw = re.search(info['options']['path_pattern'] + r'$', typed).group(0)

        dir = os.path.expandvars(pkw)
        dir = os.path.expanduser(dir)
        expanded = False
        if dir != pkw:
            expanded = True
        dir = os.path.dirname(dir)

        self.logger.debug('dir: %s', dir)

        bdirs = []
        if filepath != "":
            curdir = os.path.dirname(filepath)
            bdirs.append(('buf', curdir), )

        # full path of current file, current working dir
        cwd = self.nvim.call('getcwd')
        bdirs.append(('cwd', cwd), )

        if pkw and pkw[0] != ".":
            bdirs.append(('root', "/"))

        seen = set()
        matches = []
        for label, bdir in bdirs:
            joined_dir = os.path.join(bdir, dir.strip('/'))
            self.logger.debug('searching dir: %s', joined_dir)
            try:
                names = os.listdir(joined_dir)
                names.sort(key=lambda name: name.lower())
                self.logger.debug('search result: %s', names)
                for name in names:
                    p = os.path.join(joined_dir, name)
                    if p in seen:
                        continue
                    seen.add(p)
                    word = os.path.basename(p)
                    menu = '~' + label
                    if expanded:
                        menu += '~ ' + p
                    matches.append(dict(word=word, icase=1, menu=menu, dup=1))
            except Exception as ex:
                self.logger.info('exception on listing joined_dir [%s], %s', joined_dir, ex)
                continue

        refresh = 0
        if len(matches) > 1024:
            refresh = 1
            # pre filtering
            matches = self.matcher.process(info, ctx, startcol, matches)
            matches = matches[0:1024]

        self.logger.debug('startcol: %s, matches: %s', startcol, matches)
        self.complete(info, ctx, ctx['startcol'], matches, refresh)
