import pytest
import sys
import threading
import traceback
from time import sleep

try:
    from queue import Queue
except:
    from Queue import Queue

from .util import run_test, destroy_window

js_code = '''
window.pywebviewResult = undefined
window.pywebview.api.{0}().then(function(response) {{
    window.pywebviewResult = response
}})
'''


class Api:
    def get_number(self, params):
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

    def assertFunction(func_name, result):
        webview.evaluate_js(js_code.format(func_name))
        sleep(2.0)
        assert webview.evaluate_js('window.pywebviewResult') == result

    def _set_js_bridge(webview):
        try:
            webview.load_html('<html><body>TEST</body></html>')
            assertFunction('get_number', 5)
            assertFunction('get_string', 'test')
            q.put(0)
        except Exception as e:
            q.put(1)
            pytest.fail('Exception occured:\n{0}'.format(traceback.format_exc()))

    q = Queue()
    t = threading.Thread(target=_set_js_bridge, args=(webview,))
    t.start()

    destroy_window(webview, 10)
    webview.create_window('JSBridge test', js_api=api, debug=True)
    exitcode = q.get()
    sys.exit(exitcode)


def test_js_bridge(create_api):
    run_test(js_bridge, create_api)
