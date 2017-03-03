
# sane default for programming languages


WORD_PATTERN = {}
WORD_PATTERN['*'] =   r'(-?\d*\.\d\w*)|([^\`\~\!\@\#\$\%\^\&\*\(\)\-\=\+\[\{\]\}\\\|\;\:\'\"\,\.\<\>\/\?\s]+)'
WORD_PATTERN['php'] = r'(-?\d*\.\d\w*)|([^\-\`\~\!\@\#\%\^\&\*\(\)\=\+\[\{\]\}\\\|\;\:\'\"\,\.\<\>\/\?\s]+)'

def word_pattern(ctx):
    return WORD_PATTERN.get(ctx.get('scope_match','').lower(), None) or WORD_PATTERN['*']
