# -*- coding: utf-8 -*-

def Matcher(context, value, key='abbr', **kargs):
    context['inc_match'] = 0
    def match(b, e):
        return len(b) >= value
    return match
