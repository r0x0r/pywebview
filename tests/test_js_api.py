import webview
from .util import run_test, assert_js


def test_js_bridge():
    api = Api()
    window = webview.create_window('JSBridge test', js_api=api)
    run_test(webview, window, js_bridge)


class Api:
    def get_int(self, params):
        return 420

    def get_float(self, params):
        return 3.141

    def get_string(self, params):
        return 'test'

    def get_object(self, params):
        return {'key1': 'value', 'key2': 420}

    def get_objectlike_string(self, params):
        return '{"key1": "value", "key2": 420}'

    def get_single_quote(self, params):
        return "te'st"

    def get_double_quote(self, params):
        return 'te"st'


def js_bridge(window):
    window.load_html('<html><body>TEST</body></html>')
    assert_js(window, 'get_int', 420)
    assert_js(window, 'get_float', 3.141)
    assert_js(window, 'get_string', 'test')
    assert_js(window, 'get_object', {'key1': 'value', 'key2': 420})
    assert_js(window, 'get_objectlike_string', '{"key1": "value", "key2": 420}')
    assert_js(window, 'get_single_quote', 'te\'st')
    assert_js(window, 'get_double_quote', 'te"st')
