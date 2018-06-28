
class Sorter:
    def sort(self, matches: list):
        matches.sort(key=lambda e: e['word'].swapcase())
        return matches

