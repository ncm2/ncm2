import os
import importlib
import logging
from neovim.api import Nvim

def getLogger(name):

    def get_loglevel():
        # logging setup
        level = logging.INFO
        if 'NVIM_PYTHON_LOG_LEVEL' in os.environ:
            l = getattr(logging,
                    os.environ['NVIM_PYTHON_LOG_LEVEL'].strip(),
                    level)
            if isinstance(l, int):
                level = l
        if 'NVIM_NCM_LOG_LEVEL' in os.environ:
            l = getattr(logging,
                    os.environ['NVIM_NCM_LOG_LEVEL'].strip(),
                    level)
            if isinstance(l, int):
                level = l
        return level

    logger = logging.getLogger(__name__)
    logger.setLevel(get_loglevel())
    return logger

logger = getLogger(__name__)

# python="python2" is only used for sources that depends on python2 libraries,
# don't use it if possible
def register_source(name,abbreviation,priority,enable=True,events=[],python='python3',**kwargs):
    # implementation is put inside cm_core
    # 
    # cm_core use a trick to only register the source withou loading the entire
    # module
    return


# Base class for cm_core, sources, and scopers
class Base:

    def __init__(self,nvim):

        """
        :type nvim: Nvim
        """

        self.nvim = nvim
        self.logger = getLogger(self.__module__)

    # allow a source to preprocess inputs before committing to the manager
    @property
    def matcher(self):

        nvim = self.nvim

        if not hasattr(self,'_matcher'):

            # from cm.matchers.prifex_matcher import Matcher
            matcher_opt = nvim.eval('g:cm_matcher')
            m = importlib.import_module(matcher_opt['module'])

            chcmp_smartcase = lambda a,b: a==b if a.isupper() else a==b.lower()
            chcmp_case = lambda a,b: a==b
            chcmp_icase = lambda a,b: a.lower()==b.lower()

            case = matcher_opt.get('case','')
            if case not in ['case','icase','smartcase']:
                ignorecase,sartcase = nvim.eval('[&ignorecase,&smartcase]')
                if smartcase:
                    chcmp = chcmp_smartcase
                elif ignorecase:
                    chcmp = chcmp_icase
                else:
                    chcmp = chcmp_case
            elif case=='case':
                chcmp = chcmp_case
            elif case=='icase':
                chcmp = chcmp_icase
            else:
                # smartcase
                chcmp = chcmp_smartcase

            # cache result
            self._matcher = m.Matcher(nvim,chcmp)

        return self._matcher

    def get_pos(self, lnum , col, src):
        """
        convert vim's lnum, col into pos
        """
        lines = src.split('\n')
        pos = 0
        for i in range(lnum-1):
            pos += len(lines[i])+1
        pos += col-1

        return pos

    # convert pos into vim's lnum, col
    def get_lnum_col(self, pos, src):
        """
        convert pos into vim's lnum, col
        """
        splited = src.split("\n")
        p = 0
        for idx,line in enumerate(splited):
            if p<=pos and p+len(line)>=pos:
                return (idx+1,pos-p+1)
            p += len(line)+1

    def get_src(self,ctx):

        """
        Get the source code of current scope identified by the ctx object.
        """

        nvim = self.nvim

        bufnr = ctx['bufnr']
        changedtick = ctx['changedtick']

        key = (bufnr,changedtick)
        if key != getattr(self,'_cache_key',None):
            lines = nvim.buffers[bufnr][:]
            lines.append('') # \n at the end of buffer
            self._cache_src = "\n".join(lines)
            self._cache_key = key

        scope_offset = ctx.get('scope_offset',0)
        scope_len = ctx.get('scope_len',len(self._cache_src))

        return self._cache_src[scope_offset:scope_offset+scope_len]

    def complete(self, name, ctx, startcol, matches, refresh=False):
        if isinstance(name,dict):
            name = name['name']
        self.nvim.call('cm#complete', name, ctx, startcol, matches, refresh, async=True)

