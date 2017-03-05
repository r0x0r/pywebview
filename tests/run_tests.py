__author__ = 'roman.sirokov'

from importlib import import_module
import suite
import threading
import webview
from cocoa_util import mousemove
import unittest

def stop():
    webview.destroy_window()
    mousemove(1, 1)


if __name__ == '__main__':
    #for module in suite.__all__:
    #    test = import_module('suite.' + module)

    #    test.run()

    test = import_module('suite.simple_browser')

    suite = unittest.TestLoader().loadTestsFromTestCase(test.TestSimpleBrowser)
    unittest.TextTestRunner(verbosity=2).run(suite)
