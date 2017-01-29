# -*- coding: utf-8 -*-

# For debugging
# NVIM_PYTHON_LOG_FILE=nvim.log NVIM_PYTHON_LOG_LEVEL=INFO nvim

import os
import sys
import re
import logging
import copy
import importlib
from neovim import attach, setup_logging

logger = logging.getLogger(__name__)

class Handler:

    def __init__(self,nvim):
        self._nvim = nvim

        # { '{source_name}': {'startcol': , 'matches'}
        self._matches = {}
        self._sources = {}
        self._last_matches = []
        self._has_popped_up = False

    def cm_complete(self,srcs,name,ctx,startcol,matches,*args):
        self._sources = srcs


        try:

            # process the matches early to eliminate unnecessary complete function call
            result = self.process_matches(name,ctx,startcol,matches)

            if (not result) and (not self._matches.get(name,{}).get('last_matches',[])):
                # not popping up, ignore this request
                logger.info('Not popping up, not refreshing for cm_complete by %s, startcol %s, matches %s', name, startcol, matches)
                return

        finally:

            # storing matches

            if name not in self._matches:
                self._matches[name] = {}

            if len(matches)==0:
                del self._matches[name]
            else:
                self._matches[name]['startcol'] = startcol
                self._matches[name]['matches'] = matches

        # wait for cm_complete_timeout, reduce flashes
        if self._has_popped_up:
            self._refresh_completions(ctx)

    def cm_insert_enter(self):
        self._matches = {}

    def cm_complete_timeout(self,srcs,ctx,*args):
        if not self._has_popped_up:
            self._refresh_completions(ctx)
            self._has_popped_up = True

    # The completion core itself
    def cm_refresh(self,srcs,ctx,*args):

        self._sources = srcs
        self._has_popped_up = False

        # simple complete done
        if ctx['typed'] == '':
            self._matches = {}
        elif re.match(r'[^0-9a-zA-Z_]',ctx['typed'][-1]):
            self._matches = {}

        # do notify_sources_to_refresh
        refreshes_calls = []
        refreshes_channels = []
        for name in srcs:
            info = srcs[name]
            try:

                if (info['name'] in self._matches) and (info.get('refresh',0)==0):
                    # no need to refresh
                    continue

                if 'cm_refresh' in info:
                    refreshes_calls.append(name)
                for channel in info.get('channels',[]):
                    if 'id' in channel:
                        refreshes_channels.append(dict(name=name,id=channel['id']))
            except Exception as inst:
                logger.error('cm_refresh process exception: %s', inst)
                continue

        if not refreshes_calls and not refreshes_channels:
            logger.info('not notifying any channels, _refresh_completions now')
            self._refresh_completions(ctx)
            self._has_popped_up = True
        else:
            logger.info('cm#notify_sources_to_refresh [%s] [%s] [%s]', refreshes_calls, refreshes_channels, ctx)
            self._nvim.call('cm#notify_sources_to_refresh', refreshes_calls, refreshes_channels, ctx)

    def _refresh_completions(self,ctx):

        matches = []

        # sort by priority
        names = sorted(self._matches.keys(),key=lambda x: self._sources[x]['priority'], reverse=True)

        if len(names)==0:
            logger.info('_refresh_completions names: %s, startcol: %s, matches: %s', names, ctx['col'], matches)
            self._complete(ctx, ctx['col'], [])
            return

        startcol = ctx['col']
        base = ctx['typed'][startcol-1:]

        # basick processing per source
        for name in names:

            try:
                source_startcol = self._matches[name]['startcol']
                if source_startcol>ctx['col']:
                    self._matches[name]['last_matches'] = []
                    logger.error('ignoring invalid startcol: %s', self._matches[name])
                    continue

                source_matches = self._matches[name]['matches']
                source_matches = self.process_matches(name,ctx,source_startcol,source_matches)

                self._matches[name]['last_matches'] = source_matches

                if not source_matches:
                    continue

                # min non empty source_matches's source_startcol as startcol
                if source_startcol < startcol:
                    startcol = source_startcol

            except Exception as inst:
                logger.error('_refresh_completions process exception: %s', inst)
                continue

        # merge processing results of sources
        for name in names:

            try:
                source_startcol = self._matches[name]['startcol']
                if source_startcol>ctx['col']:
                    logger.error('ignoring invalid startcol: %s', self._matches[name])
                    continue
                source_matches = self._matches[name]['last_matches']
                prefix = ctx['typed'][startcol-1 : source_startcol-1]

                for e in source_matches:
                    e['word'] = prefix + e['word']
                    # if 'abbr' in e:
                    #     e['abbr'] = prefix + e['abbr']

                matches += source_matches

            except Exception as inst:
                logger.error('_refresh_completions process exception: %s', inst)
                continue

        logger.info('_refresh_completions names: %s, startcol: %s, matches: %s, source matches: %s', names, startcol, matches, self._matches)
        self._complete(ctx, startcol, matches)

    def process_matches(self,name,ctx,startcol,matches):

        # do some basic filtering and sorting
        result = []
        base = ctx['typed'][startcol-1:]

        for item in matches:

            e = {}
            if type(item)==type(''):
                e['word'] = item
            else:
                e = copy.deepcopy(item)

            if 'menu' not in e:
                e['menu'] = self._sources[name].get('abbreviation','')

            # For now, simply do the same word filtering as vim's doing
            # TODO: enable custom config
            if base.lower() != e['word'][0:len(base)].lower():
                continue

            result.append(e)

        # for now, simply sort them by length
        # TODO: enable custom config
        result.sort(key=lambda e: len(e['word']))

        return result


    def _complete(self, ctx, startcol, matches):
        if len(matches)==0 and len(self._last_matches)==0:
            # no need to fire complete message
            return
        self._nvim.call('cm#core_complete', ctx, startcol, matches, self._matches, async=True)

def main():

    start_type = sys.argv[1]

    if start_type == 'core':

        # use the module name here
        setup_logging('cm_core')
        logger = logging.getLogger(__name__)
        logger.setLevel(get_loglevel())

        try:
            # connect neovim
            nvim = attach('stdio')
            handler = Handler(nvim)
            logger.info('starting core, enter event loop')
            cm_core_event_loop(logger,nvim,handler)
        except Exception as ex:
            logger.info('Exception: %s',ex)

    elif start_type == 'channel':

        path = sys.argv[2]
        dir = os.path.dirname(path)
        name = os.path.splitext(os.path.basename(path))[0]

        # use the module name here
        setup_logging(name)
        logger = logging.getLogger(name)
        logger.setLevel(get_loglevel())

        try:
            # connect neovim
            nvim = attach('stdio')
            sys.path.append(dir)
            m = importlib.import_module(name)
            handler = m.Handler(nvim)
            logger.info('handler created, entering event loop')
            cm_channel_event_loop(logger,nvim,handler)
        except Exception as ex:
            logger.info('Exception: %s',ex)

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



def cm_core_event_loop(logger,nvim, handler):

    def on_setup():
        logger.info('on_setup')

    def on_request(method, args):
        raise Exception('Not implemented')

    def on_notification(method, args):
        logger.info('method: %s, args: %s', method, args)
        func = getattr(handler,method,None)
        if func is None:
            logger.info('method: %s not implemented, ignore this message', method)
            return

        func(*args)

    nvim.run_loop(on_request, on_notification, on_setup)

def cm_channel_event_loop(logger,nvim,handler):

    def on_setup():
        logger.info('on_setup')

    def on_request(method, args):
        raise Exception('Not implemented')

    def on_notification(method, args):
        logger.info('channel method: %s, args: %s', method, args)

        if method=='cm_refresh':
            ctx = args[1]
            curctx = nvim.eval('cm#context()')
            # The refresh calculation may be heavy, and the notification queue
            # may have outdated refresh events, it would be  meaningless to
            # process these event
            if ctx!=curctx:
                logger.info('ignoring outdated context (%s), current context (%s)', ctx, curctx)
                return

        func = getattr(handler,method,None)
        if func is None:
            logger.info('method: %s not implemented, ignore this message', method)
            return

        func(*args)

    nvim.run_loop(on_request, on_notification, on_setup)

main()

