import sys
import pytest
import traceback
from threading import Thread

try:
    from queue import Queue
except:
    from Queue import Queue

from .util import run_test, destroy_window


def load_html():
    import webview

    def _load_html(webview):
        try:
            webview.load_html('<h1>This is dynamically loaded HTML</h1>')
            q.put(0)
        except Exception as e:
            q.put(1)
            pytest.fail('Exception occurred:\n{0}'.format(traceback.format_exc()))
        destroy_event.set()

    q = Queue()
    t = Thread(target=_load_html, args=(webview,))
    t.start()

    destroy_event = destroy_window(webview)
    webview.create_window('URL change test', 'https://www.example.org')
    exitcode = q.get()
    sys.exit(exitcode)


def test_load_html():
    run_test(load_html)
