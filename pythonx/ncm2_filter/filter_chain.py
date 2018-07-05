from importlib import import_module

class Filter:
    def __init__(self, *opts):
        filters = []
        for opt in opts:
            if type(opt) == str:
                name = opt
                args = []
            else:
                name = opt['name']
                args = opt['args']
            modname = 'ncm2_filter.' + name
            mod = import_module(modname)
            filters.append([name, mod.Filter(*args)])
        self.filters = filters

    def filter(self, base, matches):
        for name, fl in self.filters:
            matches = fl.filter(base, matches)
        return matches
