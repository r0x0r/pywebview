import pytest
import sys
import threading

try:
    from queue import Queue
except:
    from Queue import Queue
    
from .util import run_test, destroy_window


def change_url():
    import webview

    def _change_url(webview):
        try:
            webview.load_url('http://www.google.org')
            #q.put(0)
        except Exception as e:
            pass
            #q.put(1)

    q = Queue()
    t = threading.Thread(target=_change_url, args=(webview,))

    destroy_window(webview, 5)
    webview.create_window('URL change test', 'https://www.example.org')
    exitcode = q.get()
    sys.exit(exitcode)

def test_change_url():
    run_test(change_url)
