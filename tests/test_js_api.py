from concurrent.futures.thread import ThreadPoolExecutor
import webview
from .util import run_test, assert_js


def test_js_bridge():
    api = Api()
    window = webview.create_window('JSBridge test', js_api=api)
    run_test(webview, window, js_bridge)


def test_exception():
    api = Api()
    window = webview.create_window('JSBridge test', js_api=api)
    run_test(webview, window, exception)

# This test randomly fails on Windows
def test_concurrent():
    api = Api()
    window = webview.create_window('JSBridge test', js_api=api)
    run_test(webview, window, concurrent)


class Api:
    class ApiTestException(Exception):
        pass

    def get_int(self):
        return 420

    def get_float(self):
        return 3.141

    def get_string(self):
        return 'test'

    def get_object(self):
        return {'key1': 'value', 'key2': 420}

    def get_objectlike_string(self):
        return '{"key1": "value", "key2": 420}'

    def get_single_quote(self):
        return "te'st"

    def get_double_quote(self):
        return 'te"st'

    def raise_exception(self):
        raise Api.ApiTestException()

    def echo(self, param):
        return param

    def multiple(self, param1, param2, param3):
        return param1, param2, param3


def js_bridge(window):
    window.load_html('<html><body>TEST</body></html>')
    assert_js(window, 'get_int', 420)
    assert_js(window, 'get_float', 3.141)
    assert_js(window, 'get_string', 'test')
    assert_js(window, 'get_object', {'key1': 'value', 'key2': 420})
    assert_js(window, 'get_objectlike_string', '{"key1": "value", "key2": 420}')
    assert_js(window, 'get_single_quote', 'te\'st')
    assert_js(window, 'get_double_quote', 'te"st')
    assert_js(window, 'echo', 'test', 'test')
    assert_js(window, 'multiple', [1, 2, 3], 1, 2, 3)


def exception(window):
    assert_js(window, 'raise_exception', 'error')


def concurrent(window):
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for i in range(5):
            future = executor.submit(assert_js, window, 'echo', i, i)
            futures.append(future)

    for e in filter(lambda r: r, [f.exception() for f in futures]):
        raise e
