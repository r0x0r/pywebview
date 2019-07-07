import webview
from .util import run_test, assert_js


def test_js_bridge():
    api = Api()
    window = webview.create_window('JSBridge test', js_api=api)
    run_test(webview, window, js_bridge)


class Api:
    def get_int(self, params):
        return 5

    def get_float(self, params):
        return 3.141

    def get_string(self, params):
        return 'test'


def js_bridge(window):
    window.load_html('<html><body>TEST</body></html>')
    assert_js(window, 'get_int', 5)
    assert_js(window, 'get_float', 3.141)
    assert_js(window, 'get_string', 'test')

