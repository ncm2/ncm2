from importlib import import_module

class Matcher:

    def __init__(self, *opts):
        matchers = []
        for opt in opts:
            if type(opt) == str:
                name = opt
                args = []
            else:
                name = opt['name']
                args = opt['args']
            modname = 'ncm2_matcher.' + name
            mod = import_module(modname)
            matchers.append([name, mod.Matcher(*args)])
        self.matchers = matchers

    def match(self, b, e):
        for name, m in self.matchers:
            if m.match(b, e):
                ud = e['user_data']
                if 'matcher' not in ud:
                    ud['matcher'] = name
                return True
        return False
