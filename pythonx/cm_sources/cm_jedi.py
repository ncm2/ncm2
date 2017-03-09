# -*- coding: utf-8 -*-

# For debugging
# NVIM_PYTHON_LOG_FILE=nvim.log NVIM_PYTHON_LOG_LEVEL=INFO nvim

from cm import register_source, getLogger, Base
register_source(name='cm-jedi',
                priority=9,
                abbreviation='Py',
                scoping=True,
                scopes=['python'],
                # The last two patterns is for displaying function signatures [r'\(\s?(\w*)$',r',(\s?\w*)$']
                cm_refresh_patterns=[r'^(import|from).*?\s(\w*)$',r'\.\w*$',r'\(\s?(\w*)$',r',\s?(\w*)$'],)

import re
import jedi

logger = getLogger(__name__)

class Source(Base):

    def __init__(self,nvim):
        super(Source,self).__init__(nvim)
        self._snippet_engine = nvim.vars['cm_completed_snippet_engine']

    def cm_refresh(self,info,ctx,*args):

        path = ctx['filepath']
        typed = ctx['typed']

        src = self.get_src(ctx)
        if not src.strip():
            # empty src may possibly block jedi execution, don't know why
            logger.info('ignore empty src [%s]', src)
            return

        logger.info('context [%s]', ctx)

        # logger.info('jedi.Script lnum[%s] curcol[%s] path[%s] [%s]', lnum,len(typed),path,src)
        script = jedi.Script(src, ctx['lnum'], len(ctx['typed']), path)

        if re.search(r'^(?!from|import).*?[\(\,]\s*$', typed):
            # try show the call signature
            signature_text = self._get_signature_text(script)
            if signature_text:
                matches = [dict(word='',empty=1,abbr=signature_text,dup=1),]
                # refresh=True
                # call signature popup doesn't need to be cached by the framework
                self.nvim.call('cm#complete', info['name'], ctx, ctx['col'], matches, True, async=True)
            return

        completions = script.completions()
        logger.info('completions %s', completions)

        matches = []

        for complete in completions:

            item = dict(word=ctx['base']+complete.complete,
                        icase=1,
                        dup=1,
                        menu=complete.description,
                        info=complete.docstring()
                        )

            if complete.type == 'function':
                params = []
                if hasattr(complete,'params'):
                    params = complete.params
                if not params:
                    params = []
                placeholders = []
                num = 1
                for param in params:
                    logger.info('name: %s, description: %s', param.name, param.description)
                    if re.match(r'^[\w\s]+$', param.description):
                        # param without default value
                        placeholders.append('${%s:%s}' % (num,param.name) )
                    else:
                        break
                    num += 1

                # ultisnips
                snippet = '%s(%s)${0}' % (item['word'],', '.join(placeholders))

                item['snippet'] = snippet
                logger.info('snippet: [%s] placeholders: %s', snippet, placeholders)
            # Fix the user typed case
            if item['word'].lower()==complete.name.lower():
                item['word'] = complete.name
            matches.append(item)

        # cm#complete(src, context, startcol, matches)
        logger.info('matches %s', matches)
        self.complete(info, ctx, ctx['startcol'], matches)

    def _get_signature_text(self,script):
        signature_text = ''
        # TODO: optimize
        # currently simply use the last signature
        signatures = script.call_signatures()
        logger.info('signatures: %s', signatures)
        if len(signatures)>0:
            signature = signatures[-1]
            params=[param.description for param in signature.params]
            signature_text = signature.name + '(' + ', '.join(params) + ')'
        return signature_text

