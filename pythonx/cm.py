import sys

if sys.version_info.major==2:
    from httplib import HTTPConnection
    from urlparse import urlparse
else:
    from urllib.parse import urlparse
    from http.client import HTTPConnection

import importlib
import logging

logger = logging.getLogger(__name__)

# python="python2" is only used for sources that depends on python2 libraries,
# don't use it if possible
def register_source(name,abbreviation,priority,scopes=None,cm_refresh_patterns=None,events=[],detach=0,python='python3'):
    # implementation is put inside cm_core
    # 
    # cm_core use a trick to only register the source withou loading the entire
    # module
    return

def context_outdated(ctx1,ctx2):
    # same as cm#context_changed
    # return ctx1 is None or ctx2 is None or ctx1['changedtick']!=ctx2['changedtick'] or ctx1['curpos']!=ctx2['curpos']
    # Note: changedtick is triggered when `<c-x><c-u>` is pressed due to vim's
    # bug, use curpos as workaround
    return ctx1 is None or ctx2 is None or ctx1['curpos']!=ctx2['curpos']

def get_src(ctx):
    src_uri = ctx['src_uri']
    parsed = urlparse(src_uri)
    logger.info('hostname: %s, port %s, path: %s', parsed.hostname, parsed.port, parsed.path)
    conn = HTTPConnection(parsed.hostname, parsed.port)
    try:
        conn.request("GET", src_uri)
        res = conn.getresponse()
        src = res.read().decode('utf-8')
        res.close()
        return src
    finally:
        conn.close()
    return None

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

