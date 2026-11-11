import functools
import os
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

import webview

from .util import assert_js, run_test

# A page that prepares its own window.pywebview to receive whatever pywebview writes into it
SPOOF_PAGE = """<html><head><title>spoof</title><script>
window.pywebview = {state: {}, _returnValuesCallbacks: {}};
</script></head><body>other origin</body></html>"""

PLAIN_PAGE = '<html><head><title>plain</title></head><body>other origin</body></html>'

CAPTURE_PAGE = """<html><head><title>capture</title><script>
window.eval = function(code) { window.captured = code; };
</script></head><body>other origin</body></html>"""


class Api:
    def echo(self, value):
        return value


@pytest.fixture(scope='module')
def other_origin(tmp_path_factory):
    """An HTTP server on its own origin, standing in for a site the window navigates to."""
    root = tmp_path_factory.mktemp('other_origin')
    (root / 'spoof.html').write_text(SPOOF_PAGE)
    (root / 'plain.html').write_text(PLAIN_PAGE)
    (root / 'capture.html').write_text(CAPTURE_PAGE)

    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(root))
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{server.server_address[1]}'
    server.shutdown()


def wait_for_title(window, title, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if window.run_js('document.title') == title:
            return
        time.sleep(0.2)
    raise AssertionError(f'Page "{title}" did not load')


def wait_for_api(window, timeout=10):
    deadline = time.time() + timeout
    script = 'window.pywebview && window.pywebview.api && typeof window.pywebview.api.echo'
    while time.time() < deadline:
        if window.run_js(script) == 'function':
            return
        time.sleep(0.2)
    raise AssertionError('JS API was not injected')


@pytest.mark.skipif(
    os.environ.get('PYWEBVIEW_GUI') == 'cef', reason='CEF run_js is fire-and-forget'
)
def test_navigated_origin_gets_no_api(other_origin):
    window = webview.create_window('Origins', html='<html>start</html>', js_api=Api())

    def check(window):
        assert window.evaluate_js('typeof pywebview.api.echo') == 'function'

        window.run_js(f"window.location.href = '{other_origin}/spoof.html'")
        wait_for_title(window, 'spoof')
        time.sleep(1)  # allow the load handler to run

        assert window.run_js('window.pywebview.token === undefined') is True
        assert window.run_js('window.pywebview.api === undefined') is True

        # State changes from Python must not reach the page
        window.state.secret = 'value'
        time.sleep(0.5)
        assert window.run_js('window.pywebview.state.secret === undefined') is True

        # The window UI script still runs. Cocoa keeps the native alert, so check what every
        # backend applies: the default text_select=False adds a user-select style
        has_ui_style = (
            "Array.prototype.some.call(document.querySelectorAll('style'), "
            "function (s) { return s.innerHTML.indexOf('user-select') !== -1 })"
        )
        assert window.run_js(has_ui_style) is True

    run_test(webview, window, check)


@pytest.mark.skipif(
    os.environ.get('PYWEBVIEW_GUI') == 'cef', reason='CEF run_js is fire-and-forget'
)
def test_listed_origin_gets_api(other_origin):
    webview.settings['JS_API_ALLOWED_ORIGINS'] = [other_origin]
    window = webview.create_window('Origins', html='<html>start</html>', js_api=Api())

    def check(window):
        window.run_js(f"window.location.href = '{other_origin}/plain.html'")
        wait_for_title(window, 'plain')
        wait_for_api(window)

    run_test(webview, window, check)


def test_origin_loaded_from_python_gets_api(other_origin):
    window = webview.create_window('Origins', html='<html>start</html>', js_api=Api())

    def check(window):
        window.load_url(f'{other_origin}/plain.html')
        assert window.evaluate_js('typeof pywebview.api.echo') == 'function'

    run_test(webview, window, check)


def test_blank_loaded_from_python_gets_api():
    window = webview.create_window('Blank', html='<html>start</html>', js_api=Api())

    def check(window):
        window.load_url('about:blank')
        assert window.evaluate_js('typeof pywebview.api.echo') == 'function'

    run_test(webview, window, check)


@pytest.mark.skipif(
    os.environ.get('PYWEBVIEW_GUI') == 'cef', reason='CEF run_js is fire-and-forget'
)
def test_result_after_navigation_does_not_reach_page_eval(other_origin):
    class DelayedApi:
        def __init__(self):
            self.started = threading.Event()
            self.release = threading.Event()
            self.finished = threading.Event()

        def delayed(self):
            self.started.set()
            assert self.release.wait(10)
            self.finished.set()
            return 'sensitive-api-result'

    api = DelayedApi()
    window = webview.create_window('Delayed result', html='<html>start</html>', js_api=api)

    def check(window):
        try:
            window.run_js('pywebview.api.delayed()')
            assert api.started.wait(2)
            window.run_js(f"window.location.href = '{other_origin}/capture.html'")
            wait_for_title(window, 'capture')
            api.release.set()
            assert api.finished.wait(2)
            time.sleep(0.5)
            assert window.run_js('window.captured === undefined') is True
        finally:
            api.release.set()

    run_test(webview, window, check)


@pytest.mark.skipif(
    sys.platform != 'darwin' or os.environ.get('PYWEBVIEW_GUI', 'cocoa') != 'cocoa',
    reason='WKWebView provisional navigation behavior',
)
def test_failed_provisional_navigation_preserves_bridge():
    window = webview.create_window('Navigation failure', html='<html>start</html>', js_api=Api())

    def check(window):
        token = window.evaluate_js('pywebview._bridgeToken')
        window.run_js("window.location.href = 'http://127.0.0.1:1/'")
        time.sleep(2)
        assert window.evaluate_js('pywebview._bridgeToken') == token
        assert window.evaluate_js('pywebview.api.echo !== undefined')
        assert_js(window, 'echo', 'still active', 'still active')

    run_test(webview, window, check)
