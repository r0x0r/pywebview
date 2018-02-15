import pytest
import sys
import threading
import traceback

try:
    from queue import Queue
except:
    from Queue import Queue

from .util import run_test, destroy_window


def set_title():
    import webview

    def _set_title(webview):
        try:
            webview.set_title('New title')
            q.put(0)
        except Exception as e:
            q.put(1)
            pytest.fail('Exception occured:\n{0}'.format(traceback.format_exc()))

        destroy_event.set()

    q = Queue()
    t = threading.Thread(target=_set_title, args=(webview,))
    t.start()

    destroy_event = destroy_window(webview)
    webview.create_window('Set title test', 'https://www.example.org')
    exitcode = q.get()
    sys.exit(exitcode)


def test_set_title():
    run_test(set_title)
