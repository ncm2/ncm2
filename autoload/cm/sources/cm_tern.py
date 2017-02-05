# -*- coding: utf-8 -*-

# For debugging
# NVIM_PYTHON_LOG_FILE=nvim.log NVIM_PYTHON_LOG_LEVEL=INFO nvim

import os
import re
import logging
from neovim import attach, setup_logging
import re
import subprocess
import logging
from urllib import request
import json
import cm_utils

logger = logging.getLogger(__name__)

class Tern:

    def __init__(self,bin):
        proc = subprocess.Popen([bin, '--persistent'],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL
        )
        line = proc.stdout.readline().decode('utf8')
        match = re.match(r'Listening on port (\d+)', line)

        self._port = match.group(1)

        logger.info('line %s [%s]', line, match.group(1))

        self._opener = request.build_opener()

    def completions(self, src, lnum, col, path):

        """
        :lnum: lnum zero based
        :col: col zero based
        """

        doc = {"query": {}, "files": []}
        query = doc['query']
        query['type'] = 'completions'
        query["file"] = '#0'
        query["end"] = dict(line=lnum,ch=col)

        query['lineCharPositions'] = True
        # query['expandWordForward'] = True
        query['includeKeywords'] = True
        query['caseInsensitive'] = True
        query['docs'] =  True
        query['urls'] =  True
        # type informations on completion items
        query['types'] =  True

        files = doc['files']
        files.append({"type": "full",
                      "name": path,
                      "text": src})

        return self.request(doc)

    def request(self, doc):

      try:
          payload = json.dumps(doc).encode('utf-8')
          logger.error('payload: %s', payload)
          req = self._opener.open("http://localhost:" + str(self._port) + "/", payload)
          result = req.read().decode('utf-8')
          logger.error('result: %s', result)
          return json.loads(result)
      except Exception as ex:
          logger.error('exception: %s', ex)
          return None


class Handler:

    def __init__(self,nvim):

        self._nvim = nvim
        logger.info('eval for tern: %s', 'split(globpath(&rtp,"node_modules/tern/bin/tern",1),"\\n")[0]')
        path = nvim.eval('split(globpath(&rtp,"node_modules/tern/bin/tern",1),"\\n")[0]')
        self._tern = Tern(path)
        logger.info('eval result: %s', path)

    def cm_refresh(self,info,ctx,*args):

        lnum = ctx['lnum']
        col = ctx['col']
        typed = ctx['typed']

        kwtyped = re.search(r'[0-9a-zA-Z_]*?$',typed).group(0)
        startcol = col-len(kwtyped)

        path, filetype = self._nvim.eval('[expand("%:p"),&filetype]')
        if filetype not in ['javascript','javascript.jsx','markdown']:
            logger.info('ignore filetype: %s', filetype)
            return

        src = "\n".join(self._nvim.current.buffer[:])

        if filetype=='markdown':
            # setup completions for markdown file
            result = cm_utils.check_markdown_code_block(src, ['javascript', 'javascript.jsx'], lnum, col)
            logger.info('try markdown, %s,%s,%s, result: %s', src, col, col, result)
            if result is None:
                return
            src = result['src']
            col = result['col']
            lnum = result['lnum']

        # completion pattern
        if (re.search(r'[\w_]{2,}$',typed)
            or re.search(r'\.[\w_]*$',typed)
            ):
            pass
        else:
            return

        completions = self._tern.completions(src,lnum-1,len(typed),path)
        logger.info('completions %s', completions)

        if not completions or not completions.get('completions',None):
            return

        matches = []

        for complete in completions['completions']:
            
            item = dict(word=complete['name'],
                        icase=1,
                        dup=1,
                        menu=complete.get('type',''),
                        info=complete.get('doc',''),
                        )
            matches.append(item)

        # cm#complete(src, context, startcol, matches)
        ret = self._nvim.call('cm#complete', info['name'], ctx, startcol, matches)
        logger.info('matches %s, ret %s', matches, ret)

