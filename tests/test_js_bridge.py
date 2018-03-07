import pytest
import sys
import threading
import traceback
from time import sleep

try:
    from queue import Queue
except:
    from Queue import Queue

from .util import run_test, destroy_window, assert_js


class Api:
    def get_int(self, params):
        return 5

    def get_float(self, params):
        return 3.141

    def get_string(self, params):
        return 'test'


@pytest.fixture
def create_api():
    return Api()


def js_bridge(api):
    import webview

    def _set_js_bridge(webview):
        try:
            webview.load_html('<html><body>TEST</body></html>')
            assert_js(webview, 'get_int', 5)
            assert_js(webview, 'get_float', 3.141)
            assert_js(webview, 'get_string', 'test')
            q.put(0)
        except Exception as e:
            q.put(1)
            pytest.fail('Exception occured:\n{0}'.format(traceback.format_exc()))
        destroy_event.set()

    q = Queue()
    t = threading.Thread(target=_set_js_bridge, args=(webview,))
    t.start()

    destroy_event = destroy_window(webview)
    webview.create_window('JSBridge test', js_api=api)
    exitcode = q.get()
    sys.exit(exitcode)


def test_js_bridge(create_api):
    run_test(js_bridge, create_api)
