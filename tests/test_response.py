import os
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
        return 'test'

    window = webview.create_window('Response test', app, width=800, height=600)
    return window


def _qt_without_response_event():
    # QT emits response_received from QWebEngineLoadingInfo.responseHeaders(), added in Qt 6.6
    if os.environ.get('PYWEBVIEW_GUI') != 'qt':
        return False

    from qtpy import QT_VERSION

    return tuple(int(part) for part in QT_VERSION.split('.')[:2]) < (6, 6)


@pytest.mark.skipif(
    _qt_without_response_event(),
    reason='response_received requires Qt 6.6 or newer',
)
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
    lock.acquire()
    window.events.response_received += on_response
    run_test(webview, window, response_test, (exceptions, lock))


def response_test(window, exceptions, lock):
    assert lock.acquire(timeout=10)
    if len(exceptions) > 0:
        raise exceptions[0]
