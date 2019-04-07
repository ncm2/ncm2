import sys
import os
from importlib import import_module
import logging
import platform
import subprocess
from subprocess import Popen
from os import path
import unicodedata
from copy import deepcopy
import json
import time

__all__ = ['Ncm2Base', 'Ncm2Source', 'Popen']

if platform.system() == 'Windows':
    cls = Popen
    # redefine popen

    class Popen(cls):
        def __init__(self, *args, **keys):
            if 'startupinfo' not in keys:
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                keys['startupinfo'] = si
            cls.__init__(self, *args, **keys)


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
        if 'NVIM_NCM2_LOG_LEVEL' in os.environ:
            l = getattr(logging,
                        os.environ['NVIM_NCM2_LOG_LEVEL'].strip(),
                        level)
            if isinstance(l, int):
                level = l
        return level

    logger = logging.getLogger(__name__)
    logger.setLevel(get_loglevel())
    return logger

logger = getLogger(__name__)

def matcher_get(context, opt=None):
    if 'matcher' in context:
        if opt is None:
            opt = context['matcher']
    elif opt is None:
        # FIXME This is only for backword compability
        opt = context
        context = {}
    name = opt['name']
    modname = 'ncm2_matcher.' + name
    mod = import_module(modname)
    # Some matchers, e.g. equal matcher, need to disable the incremental
    # match feature. It needs a way to set inc_match=0. This is why we need
    # to pass context to the matcher.
    m = mod.Matcher(context=context, **opt)
    return m

def matcher_opt_formalize(opt):
    if type(opt) is str:
        return dict(name=opt)
    return deepcopy(opt)

class Ncm2Base:
    def __init__(self, nvim):
        self.nvim = nvim

    def matcher_opt_formalize(self, opt):
        return matcher_opt_formalize(opt)

    def matcher_get(self, context):
        return matcher_get(context)

    def match_formalize(self, ctx, item):
        e = {}
        if type(item) is str:
            e['word'] = item
        else:
            e = deepcopy(item)

        e['icase'] = 1
        e['equal'] = 1
        if 'menu' not in e or type(e['menu']) != str:
            e['menu'] = ''
        if 'info' not in e or type(e['info']) != str:
            e['info'] = ''
        if 'abbr' not in e or type(e['abbr']) != str:
            e['abbr'] = e['word']
        if 'kind' not in e or type(e['kind']) != str:
            e['kind'] = ''

        # LanguageClient-neovim sends json-encoded user_data
        if type(e.get('user_data', None)) is str:
            try:
                e['user_data'] = json.loads(item['user_data'])
            except:
                pass

        if 'user_data' not in e or type(e['user_data']) != dict:
            e['user_data'] = {}

        ud = e['user_data']
        ud['source'] = ctx['source']
        ud['ncm2'] = 1
        return e

    def matches_formalize(self, ctx, matches):
        formalized = []
        for e in matches:
            formalized.append(self.match_formalize(ctx, e))
        return formalized

    def lccol2pos(self, lnum, ccol, src):
        """
        convert lnum, ccol into pos
        """
        lines = src.splitlines() or [""]

        pos = 0
        for i in range(lnum - 1):
            pos += len(lines[i]) + 1
        pos += ccol - 1

        return pos

    def pos2lccol(self, pos, src):
        """
        convert pos into lnum, ccol
        """
        lines = src.splitlines() or [""]
        p = 0
        for idx, line in enumerate(lines):
            if p <= pos and p + len(line) >= pos:
                return (idx + 1, pos - p + 1)
            p += len(line) + 1

    def get_src(self, src, ctx):
        """
        Get the source code of current scope identified by the ctx object.
        """
        bufnr = ctx['bufnr']
        changedtick = ctx['changedtick']

        scope_offset = ctx.get('scope_offset', 0)
        scope_len = ctx.get('scope_len', len(src))

        return src[scope_offset: scope_offset + scope_len]

    def update_rtp(self, rtp):
        for ele in rtp.split(','):
            pyx = path.join(ele, 'pythonx')
            if pyx not in sys.path:
                sys.path.append(pyx)
            py3 = path.join(ele, 'python3')
            if py3 not in sys.path:
                sys.path.append(py3)

    def strdisplaywidth(self, s):
        def get_char_display_width(unicode_str):
            r = unicodedata.east_asian_width(unicode_str)
            if r == "F":  # Fullwidth
                return 1
            elif r == "H":  # Half-width
                return 1
            elif r == "W":  # Wide
                return 2
            elif r == "Na":  # Narrow
                return 1
            elif r == "A":  # Ambiguous, go with 2
                return 1
            elif r == "N":  # Neutral
                return 1
            else:
                return 1

        s = unicodedata.normalize('NFC', s)
        w = 0
        for c in s:
            w += get_char_display_width(c)
        return w


class Ncm2Source(Ncm2Base):
    def __init__(self, nvim):
        Ncm2Base.__init__(self, nvim)

        # add lazy_check_context to on_complete method
        on_complete_impl = self.on_complete
        def on_complete(context, *args):
            if not self.lazy_check_context(context):
                logger.info('on_complete lazy_check_context failed')
                return
            on_complete_impl(context, *args)
        self.on_complete = on_complete
        logger.debug('on_complete is wrapped')

    def lazy_check_context(self, context):
        if context.get('dated', 0):
            return False
        # only checks when we receives a context that seems old
        now = time.time()
        if now >= context['time'] + 0.5:
            return not self.nvim.call('ncm2#complete_context_dated', context)
        else:
            return True

    def complete(self, ctx, startccol, matches, refresh=False):
        self.nvim.call('ncm2#complete', ctx, startccol,
                       matches, refresh, async_=True)
