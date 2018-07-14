
def Sorter(**kargs):
    def sort(matches: list):
        matches.sort(key=lambda e: e['word'].swapcase())
        return matches
    return sort

