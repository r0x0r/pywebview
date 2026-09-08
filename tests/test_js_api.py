from concurrent.futures.thread import ThreadPoolExecutor

import webview

from .util import assert_js, run_test


def test_js_bridge():
    api = Api()
    window = webview.create_window(
        'JSBridge test', html='<html><body>TEST</body></html>', js_api=api
    )
    run_test(webview, window, js_bridge)


def test_exception():
    api = Api()
    window = webview.create_window(
        'JSBridge test', html='<html><body>TEST</body></html>', js_api=api
    )
    run_test(webview, window, exception)


# This test randomly fails on Windows
def test_concurrent():
    api = Api()
    window = webview.create_window(
        'JSBridge test', html='<html><body>TEST</body></html>', js_api=api
    )
    run_test(webview, window, concurrent)


def test_skip_existing():
    api = Api()
    window = webview.create_window(
        'JSBridge test', html='<html><body>TEST</body></html>', js_api=api
    )
    run_test(webview, window, skip_existing)


def test_recursive_attribute():
    api = RecursiveApi()
    window = webview.create_window(
        'JSBridge test', html='<html><body>TEST</body></html>', js_api=api
    )
    # Reproduce issue #1838: storing the window on the js_api object used to make
    # function exposure walk into window.native and recurse until a RecursionError.
    api.window = window
    run_test(webview, window, recursive_attribute)


class NestedApi:
    @classmethod
    def get_int(cls):
        return 422

    def get_int_instance(self):
        return 423


class _Generative:
    # Returns a fresh object on every attribute access, so the id() cycle guard never
    # matches - mimicking native objects such as
    # AccessibilityObject.Owner.AccessibilityObject.Owner... Only the depth limit stops
    # the recursion here. See issue #1838.
    def node_method(self):
        return 'node'

    @property
    def child(self):
        return _Generative()


class RecursiveApi:
    # Exposes an infinitely deep object graph that must not crash function exposure with
    # a RecursionError. See issue #1838.
    generative = _Generative()

    def get_int(self):
        return 420


class Api:
    class ApiTestException(Exception):
        pass

    nested = NestedApi
    nested_instance = NestedApi()
    nested_instance_duplicate = nested_instance

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
    assert_js(window, 'get_int', 420)
    assert_js(window, 'get_float', 3.141)
    assert_js(window, 'get_string', 'test')
    assert_js(window, 'get_object', {'key1': 'value', 'key2': 420})
    assert_js(window, 'get_objectlike_string', '{"key1": "value", "key2": 420}')
    assert_js(window, 'get_single_quote', "te'st")
    assert_js(window, 'get_double_quote', 'te"st')
    assert_js(window, 'echo', 'test', 'test')
    assert_js(window, 'multiple', [1, 2, 3], 1, 2, 3)
    assert_js(window, 'nested.get_int', 422)
    assert_js(window, 'nested_instance.get_int_instance', 423)


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


def skip_existing(window):
    assert window.evaluate_js('window.pywebview.api.nested_instance_duplicate === undefined')


def recursive_attribute(window):
    # The window must load and expose real methods without crashing on the
    # infinitely deep `generative` attribute.
    assert_js(window, 'get_int', 420)
