
def Matcher(**kargs):
    def match(b, m):
        m['user_data']['match_highlight'] = []
        return True
    return match
