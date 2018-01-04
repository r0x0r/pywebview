import pytest
import sys
import threading
import traceback

try:
    from queue import Queue
except:
    from Queue import Queue

from .util import run_test, destroy_window


class Api:
    def get_number(self):
        return 5

    def get_string(self):
        return 'test'

@pytest.fixture
def create_api():
    return Api()

def js_bridge(api):
    import webview

    def _set_js_bridge(webview):
        try:
            webview.load_html('<html><body></body></html>')
            assert webview.evaluate_js('pywebview.api.get_number()') == 5
            assert webview.evaluate_js('pywebview.api.get_string()') == 'test'
            q.put(0)
        except Exception as e:
            q.put(1)
            pytest.fail('Exception occured:\n{0}'.format(traceback.format_exc()))

    q = Queue()
    t = threading.Thread(target=_set_js_bridge, args=(webview,))
    t.start()

    destroy_window(webview)
    webview.create_window('JSBridge test', js_api=api)
    exitcode = q.get()
    sys.exit(exitcode)


def test_js_bridge(create_api):
    run_test(js_bridge, create_api)
