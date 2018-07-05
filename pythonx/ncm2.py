import sys
import os
from importlib import import_module
import logging
from neovim import attach, setup_logging
import platform
from subprocess import Popen
from os import path
import unicodedata
from copy import deepcopy

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


class Ncm2Base:
    def __init__(self, nvim):
        self.nvim = nvim

    def matcher_get(self, opts):
        if type(opts) != list:
            opts = [opts]
        from ncm2_matcher.match_any import Matcher
        m = Matcher(*opts)
        return lambda *args: m.match(*args)

    def sorter_get(self, opt):
        fields = opt.split(',')
        name = fields[0]
        args = fields[1:]
        mod = import_module('ncm2_sorter.' + name)
        sorter = mod.Sorter(*args)
        return lambda matches: sorter.sort(matches)

    def match_formalize(self, ctx, item):
        e = {}
        if type(item) == type(''):
            e['word'] = item
        else:
            e = deepcopy(item)

        e['icase'] = 1
        if 'menu' not in e or type(e['menu']) != str:
            e['menu'] = ''
        if 'info' not in e or type(e['menu']) != str:
            e['info'] = ''
        if 'abbr' not in e or type(e['abbr']) != str:
            e['abbr'] = e['word']

        if 'user_data' not in e or type(e['user_data']) != dict:
            e['user_data'] = {}

        ud = e['user_data']
        ud['source'] = ctx['source']['name']
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

    def complete(self, ctx, startccol, matches, refresh=False):
        self.nvim.call('ncm2#complete', ctx, startccol,
                       matches, refresh, async_=True)
