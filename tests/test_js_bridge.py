import webview

from .util import run_test2, assert_js


class Api:
    def get_int(self, params):
        return 5

    def get_float(self, params):
        return 3.141

    def get_string(self, params):
        return 'test'


def main_func():
    api = Api()
    webview.create_window('JSBridge test', js_api=api)


def js_bridge():
    webview.load_html('<html><body>TEST</body></html>')
    assert_js(webview, 'get_int', 5)
    assert_js(webview, 'get_float', 3.141)
    assert_js(webview, 'get_string', 'test')


def test_js_bridge():
    run_test2(main_func, js_bridge, webview)
