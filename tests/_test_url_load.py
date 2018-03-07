import pytest
import sys
import threading
import traceback

try:
    from queue import Queue
except:
    from Queue import Queue
    
from .util import run_test, destroy_window


def url_load():
    import webview

    def _change_url(webview):
        try:
            webview.load_url('https://www.google.org')
            q.put(0)
        except Exception as e:
            q.put(1)
            pytest.fail('Exception occured:\n{0}'.format(traceback.format_exc()))
        destroy_event.set()

    q = Queue()
    t = threading.Thread(target=_change_url, args=(webview,))
    t.start()

    destroy_event = destroy_window(webview)
    webview.create_window('URL change test', 'https://www.example.org')
    exitcode = q.get()
    sys.exit(exitcode)


def test_url_load():
    run_test(url_load)
