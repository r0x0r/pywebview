from threading import Lock
import pytest

import webview

from .util import run_test
from bottle import Bottle

@pytest.fixture
def window():
    app = Bottle()

    @app.route('/')
    def index():
        return 'test'

    window = webview.create_window('Response test', app, width=800, height=600)
    return window


def test_response_event(window):
    def on_response(response):
        if 'favicon' in response.url:
            return

        try:
            assert response.status_code == 200
            assert '127.0.0.1' in response.url
            assert 'text/html' in response.headers['Content-Type']
            assert response.headers['Content-Length'] == '4'
            if lock.locked():
                lock.release()
        except AssertionError as e:
            exceptions.append(e)

    lock = Lock()
    exceptions = []
    window.events.response_received += on_response
    run_test(webview, window, response_test, (exceptions, lock))


def response_test(window, exceptions, lock):
    lock.acquire()
    if len(exceptions) > 0:
        raise exceptions[0]
