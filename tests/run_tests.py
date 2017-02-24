__author__ = 'roman.sirokov'

from importlib import import_module
import suite


if __name__ == '__main__':
    for module in suite.__all__:
        spec = import_module('suite.' + module)

        try:
            spec.run()
        except Exception as e:
            print(e)