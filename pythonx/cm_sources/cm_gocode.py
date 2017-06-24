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

register_source(name='cm-gocode',
                priority=9,
                abbreviation='Go',
                word_pattern=r'[\w/]+',
                early_cache=1,
                scoping=True,
                scopes=['go'],
                cm_refresh_patterns=[r'\.'],)

import re
import subprocess
import json

logger = getLogger(__name__)


class Source(Base):

    def __init__(self,nvim):
        super(Source,self).__init__(nvim)
        self._checked = False

        try:
            from distutils.spawn import find_executable
            # echoe does not work here
            if not find_executable("gocode"):
                self.message('error', "Can't find [gocode] binary. Please install gocode http://github.com/nsf/gocode")
        except:
            pass

    def get_pos(self, lnum , col, src):
        lines = src.split(b'\n')
        pos = 0
        for i in range(lnum-1):
            pos += len(lines[i])+1
        pos += col-1
        return pos

    def cm_refresh(self,info,ctx,*args):

        # Note:
        # 
        # If you'r implementing you own source, and you want to get the content
        # of the file, Please use `cm.get_src()` instead of
        # `"\n".join(self._nvim.current.buffer[:])`

        src = self.get_src(ctx).encode('utf-8')
        filepath = ctx['filepath']

        # convert lnum, col to offset
        offset = self.get_pos(ctx['lnum'],ctx['col'],src)

        # invoke gocode
        proc = subprocess.Popen(args=['gocode','-f','json','autocomplete', filepath,'%s' % offset], 
                                stdin=subprocess.PIPE, 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.DEVNULL)

        result, errs = proc.communicate(src,timeout=30)
        # result: [1, [{"class": "func", "name": "Print", "type": "func(a ...interface{}) (n int, err error)"}, ...]]
        result = json.loads(result.decode('utf-8')) 
        logger.info("result %s", result)
        if not result:
            return

        completions = result[1]
        startcol = ctx['col'] - result[0]

        if startcol==ctx['col'] and re.match(r'\w', ctx['typed'][-1]):
            # workaround gocode bug when completion is triggered in a golang
            # string
            return

        if not completions:
            return

        matches = []

        for complete in completions:

            # {
            #     "class": "func",
            #     "name": "Fprintln",
            #     "type": "func(w !io!io.Writer, a ...interface{}) (n int, err error)"
            # },

            item = dict(word=complete['name'],
                        icase=1,
                        dup=1,
                        menu=complete.get('type',''),
                        # info=complete.get('doc',''),
                        )

            matches.append(item)

            # snippet support
            if 'class' in complete and complete['class']=='func' and 'type' in complete:
                m = re.search(r'func\((.*?)\)',complete['type'])
                if not m:
                    continue
                params = m.group(1)
                params = params.split(',')
                logger.info('snippet params: %s',params)
                snip_params = []
                num = 1
                optional = ''
                for param in params:
                    param = param.strip()
                    if not param:
                        logger.error("failed to process snippet for item: %s, param: %s", item, param)
                        break
                    name = param.split(' ')[0]
                    if param.find('...')>=0:
                        # optional args
                        if num>1:
                            optional += '${%s:, %s...}' % (num, name)
                        else:
                            optional += '${%s:%s...}' % (num, name)
                        break
                    snip_params.append("${%s:%s}" % (num,name))
                    num += 1

                item['snippet'] = item['word'] + '(' + ", ".join(snip_params) + optional + ')${0}'

        logger.info('startcol %s, matches %s', startcol, matches)
        self.complete(info, ctx, startcol, matches)

