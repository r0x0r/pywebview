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


# Only request_sent is covered: header modification and response_received both
# need the custom-request path in PyWebViewClient, which is skipped for the
# cleartext localhost URLs the built-in server serves here.
def test_request_event(window):
    def on_request(window, request):
        try:
            assert request.method == 'GET'
            assert '127.0.0.1' in request.url
        except AssertionError as e:
            exceptions.append(e)
        finally:
            if lock.locked():
                lock.release()

    lock = Lock()
    exceptions = []
    lock.acquire()
    window.events.request_sent += on_request
    run_test(webview, window, request_test, (exceptions, lock))


def request_test(window, exceptions, lock):
    assert lock.acquire(timeout=10)

    if len(exceptions) > 0:
        raise exceptions[0]
