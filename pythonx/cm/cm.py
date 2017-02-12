import re
import logging
import urllib
import http.client
import copy

logger = logging.getLogger(__name__)

def register_source(name,abbreviation,priority,scopes=None,cm_refresh_patterns=None,events=[],detach=0):
    # implementation is put inside cm_core
    # 
    # cm_core use a trick to only register the source withou loading the entire
    # module
    return

def context_outdated(ctx1,ctx2):
    # same as cm#context_changed
    return ctx1 is None or ctx2 is None or ctx1['changedtick']!=ctx2['changedtick'] or ctx1['curpos']!=ctx2['curpos']

def get_src(ctx):
    src_uri = ctx['src_uri']
    parsed = urllib.parse.urlparse(src_uri)
    logger.info('hostname: %s, port %s, path: %s', parsed.hostname, parsed.port, parsed.path)
    conn = http.client.HTTPConnection(parsed.hostname, parsed.port)
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

def smart_case_prefix_matcher(base,item):
    if len(base)>len(item['word']):
        return False
    for a,b in zip(base,item['word']):
        if a.isupper() :
            if a!=b:
                return False
        elif a!=b.lower():
            return False
    return True

def alnum_sorter(base,startcol,matches):
    # in python, 'A' sort's before 'a', we need to swapcase for the 'a'
    # sorting before 'A'
    matches.sort(key=lambda e: e['word'].swapcase())
    return matches

