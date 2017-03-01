import os
import sys
import importlib
import logging
from neovim.api import Nvim
from neovim import setup_logging, attach

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
        return level

    logger = logging.getLogger(__name__)
    logger.setLevel(get_loglevel())
    return logger

logger = getLogger(__name__)

# python="python2" is only used for sources that depends on python2 libraries,
# don't use it if possible
def register_source(name,abbreviation,priority,enable=True,events=[],detach=0,python='python3',**kwargs):
    # implementation is put inside cm_core
    # 
    # cm_core use a trick to only register the source withou loading the entire
    # module
    return

def get_src(nvim,ctx):
    """
    :type nvim: Nvim
    """

    bufnr = ctx['bufnr']
    changedtick = ctx['changedtick']

    key = (bufnr,changedtick)
    if key != getattr(get_src,'_cache_key',None):
        lines = nvim.buffers[bufnr][:]
        get_src._cache_src = "\n".join(lines)
        get_src._cache_key = key

    scope_offset = ctx.get('scope_offset',0)
    scope_len = ctx.get('scope_len',len(get_src._cache_src))

    return get_src._cache_src[scope_offset:scope_offset+scope_len]


# convert (lnum, col) to pos
def get_pos(lnum,col,src):

    # curpos
    lines = src.split('\n')
    pos = 0
    for i in range(lnum-1):
        pos += len(lines[i])+1
    pos += col-1

    return pos

def get_lnum_col(pos,src):
    splited = src.split("\n")
    p = 0
    for idx,line in enumerate(splited):
        if p<=pos and p+len(line)>=pos:
            return (idx+1,pos-p+1)
        p += len(line)+1

# allow a source to preprocess inputs before commit to the manager
def get_matcher(nvim):

    if hasattr(get_matcher,'matcher'):
        return get_matcher.matcher

    # from cm.matchers.prifex_matcher import Matcher
    matcher_opt = nvim.eval('g:cm_matcher')
    m = importlib.import_module(matcher_opt['module'])

    def chcmp_smartcase(a,b):
        if a.isupper():
            return a==b
        else:
            return a == b.lower()

    def chcmp_case(a,b):
        return a==b

    def chcmp_icase(a,b):
        return a.lower()==b.lower()

    chcmp = None
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
    elif case=='smartcase':
        chcmp = chcmp_smartcase

    # cache result
    get_matcher.matcher = m.Matcher(nvim,chcmp)
    return get_matcher.matcher

