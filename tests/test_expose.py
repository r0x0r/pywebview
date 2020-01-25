from concurrent.futures.thread import ThreadPoolExecutor
import webview
from .util import run_test, assert_js


def test_expose_single():
    window = webview.create_window('JSBridge test', html='<html><body>TEST</body></html>')
    window.expose(get_int)
    run_test(webview, window, expose_single)


def test_expose_multiple():
    window = webview.create_window('JSBridge test', html='<html><body>TEST</body></html>')
    window.expose(get_int, get_float)
    run_test(webview, window, expose_multiple)


def test_expose_runtime():
    window = webview.create_window('JSBridge test', html='<html><body>TEST</body></html>')
    run_test(webview, window, expose_runtime)


def test_override():
    api = Api()
    window = webview.create_window('JSBridge test', js_api=api)
    window.expose(get_int)
    run_test(webview, window, expose_override)


def get_int():
    return 420


def get_float():
    return 420.420


class Api:
    def get_int(self):
        return 421


def expose_single(window):
    assert_js(window, 'get_int', 420)


def expose_multiple(window):
    assert_js(window, 'get_int', 420)
    assert_js(window, 'get_float', 420.420)


def expose_runtime(window):
    window.expose(get_int, get_float)
    assert_js(window, 'get_int', 420)


def expose_override(window):
    assert_js(window, 'get_int', 420)