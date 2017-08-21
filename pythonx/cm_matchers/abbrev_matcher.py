# -*- coding: utf-8 -*-

import distutils.spawn
import os
import pipes
import shlex
import subprocess


def _word_boundary(prev, curr):
    """Whether current character is on word boundary."""
    if not prev:
        return True
    return ((curr.isupper() and not prev.isupper()) or
            (curr.islower() and not prev.isalpha()) or
            (curr.isdigit() and not prev.isdigit()) or
            (not curr.isalnum() and curr != prev))


def _match_generator(pattern, string, offset=0):
    """Recursively generate matches of `pattern` in `string`."""

    def _find_ignorecase(string, char, start=0):
        """Find first occurrence of `char` inside `string`,
           starting with `start`-th character."""
        if char.isalpha():
            lo = string.find(char.lower(), start)
            hi = string.find(char.upper(), start)
            if lo == -1:
                return hi
            elif hi == -1:
                return lo
            else:
                return min(hi, lo)
        else:
            return string.find(char, start)

    if pattern == '':
        yield []
        return

    if string == '':
        return

    indices = range(len(string))

    abbrev_0 = pattern[0]
    abbrev_rest = pattern[1:]

    if abbrev_0.lower() == string[0].lower():
        matches = _match_generator(abbrev_rest, string[1:], offset + 1)
        for m in matches:
            m.insert(0, offset)
            yield m

    i = _find_ignorecase(string, abbrev_0, 1)
    while i != -1:
        curr = string[i]

        prev = string[i - 1]
        if _word_boundary(prev, curr):
            matches = _match_generator(abbrev_rest, string[i + 1:],
                                       offset + i + 1)
            for m in matches:
                m.insert(0, offset + i)
                yield m

        i = _find_ignorecase(string, abbrev_0, i + 1)


def make_regex(pattern, escape=False):
    """Build regular expression corresponding to `pattern`."""

    def re_group(r):
        return r'(' + r + r')'

    def re_or(r1, r2):
        return re_group(re_group(r1) + '|' + re_group(r2))

    def re_opt(r):
        return re_group(r) + '?'

    asterisk = '*'
    res = ''
    res += '^'
    for i, ch in enumerate(pattern):
        match_start = ''

        if ch.isalpha():
            ch_lower = ch.lower()
            ch_upper = ch.upper()
            not_alpha = '[^a-zA-Z]'
            not_upper = '[^A-Z]'
            anycase = (re_opt(r'.{asterisk}{not_alpha}') + '{match_start}' +
                       '[{ch_lower}{ch_upper}]')
            camelcase = re_opt(r'.{asterisk}{not_upper}') + '{ch_upper}'
            ch_res = re_or(anycase, camelcase)
        elif ch.isdigit():
            ch_res = (re_opt(r'.{asterisk}[^0-9]') + '{match_start}{ch}')
        else:
            ch_res = r'.{asterisk}\{match_start}{ch}'
        res += ch_res.format(**locals())
    if escape:
        res = res.replace('\\', '\\\\')
    return res


def is_exe(path):
    return os.path.isfile(path) and os.access(path, os.X_OK)


def which(exe):
    if not is_exe(exe):
        found = distutils.spawn.find_executable(exe)
        if found is not None and is_exe(found):
            return found
    return exe


def filter_grep(regex, strings, cmd='ag --numbers'):
    """Return list of indexes in `strings` which match `regex`"""
    arg_list = shlex.split(cmd)
    arg_list[0] = which(arg_list[0])
    arg_list.append(regex)
    cmd_str = ' '.join(pipes.quote(arg) for arg in arg_list)

    popen_kwargs = dict(creationflags=0x08000000) if os.name == 'nt' else {}
    try:
        grep = subprocess.Popen(arg_list,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, **popen_kwargs)
    except BaseException as exc:
        msg = 'Exception when executing "{}": {}'.format(cmd_str, exc)
        raise Exception(msg)
    out, err = grep.communicate(b'\n'.join([i.encode() for i in strings]))
    if err or grep.returncode == 2:
        msg = 'Command "{}" exited with return code {} and stderr "{}"'.format(
            cmd_str, grep.returncode, err.strip())
        raise Exception(msg)
    res = []
    for out_str in out.splitlines():
        splitted = out_str.split(b':', 1)
        try:
            assert len(splitted) == 2
            line_num = int(splitted[0])
        except:
            msg = 'Output "{}" does not contain line number (wrong grep arguments?)'
            raise Exception(msg.format(out_str))
        res.append(line_num - 1)
    return res


class Matcher(object):

    def __init__(self,nvim,chcmp,*args):
        self._chcmp = chcmp

    def process(self,info,ctx,startcol,matches):

        # generator to list
        matches = list(matches)

        # fix for chinese characters
        # `你好 abcd|`
        # has  col('.')==11 on vim
        # the evaluated startcol is: startcol[8] typed[你好 abcd]
        # but in python, "你好 abcd"[8] is not a valid index
        begin = -(ctx['col'] - startcol)
        base = ''
        if begin:
            base = ctx['typed'][begin:]
        regex = make_regex(base)
        tmp = [item['word'] for item in matches]
        indices = filter_grep(regex, tmp)

        return [matches[i] for i in indices]

