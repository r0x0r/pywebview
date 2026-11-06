import functools
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

import webview

from .util import run_test

# A page that prepares its own window.pywebview to receive whatever pywebview writes into it
SPOOF_PAGE = """<html><head><title>spoof</title><script>
window.pywebview = {state: {}, _returnValuesCallbacks: {}};
</script></head><body>other origin</body></html>"""

PLAIN_PAGE = '<html><head><title>plain</title></head><body>other origin</body></html>'


class Api:
    def echo(self, value):
        return value


@pytest.fixture(scope='module')
def other_origin(tmp_path_factory):
    """An HTTP server on its own origin, standing in for a site the window navigates to."""
    root = tmp_path_factory.mktemp('other_origin')
    (root / 'spoof.html').write_text(SPOOF_PAGE)
    (root / 'plain.html').write_text(PLAIN_PAGE)

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

    run_test(webview, window, check)


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
