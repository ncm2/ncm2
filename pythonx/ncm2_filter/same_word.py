
class Filter:
    def filter(self, b, matches):
        return list(filter(lambda m: b != m['word'], matches))
