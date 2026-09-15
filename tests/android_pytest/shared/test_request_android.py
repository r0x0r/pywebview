from threading import Lock

import pytest
from bottle import Bottle

import webview

from .util import run_test


@pytest.fixture
def window():
    app = Bottle()

    @app.route('/')
    def index():
        return '<html><body>request test</body></html>'

    return webview.create_window('Request test', app)


# test_request.py's second test can't be reused: modifying the request headers
# only takes effect on the custom-request path in PyWebViewClient, and that path
# is skipped for cleartext localhost URLs, which is what the built-in server
# serves here (see buildozer.spec on why ssl=True is not available). The same
# limitation means response_received never fires, so there is no Android
# equivalent of test_response.py.
def test_request_event(window):
    def on_request(_, request):
        try:
            assert request.method == 'GET'
            assert '127.0.0.1' in request.url

            if lock.locked():
                lock.release()
        except AssertionError as e:
            exceptions.append(e)

    lock = Lock()
    exceptions = []
    lock.acquire()
    window.events.request_sent += on_request
    run_test(webview, window, request_test, (exceptions, lock))


def request_test(window, exceptions, lock):
    assert lock.acquire(timeout=10)

    if len(exceptions) > 0:
        raise exceptions[0]
