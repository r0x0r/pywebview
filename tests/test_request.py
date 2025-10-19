from threading import Lock

import pytest
from bottle import Bottle, request

import webview

from .util import run_test


@pytest.fixture
def headers_window():
    app = Bottle()

    @app.route('/')
    def display_headers():
        headers = dict(request.headers)
        return '<br>'.join(f'{key}: {value}' for key, value in headers.items())

    window = webview.create_window('Headers test', app, width=800, height=600)
    return window


def test_request_event(headers_window):
    def on_request(window, request):
        try:
            assert request.method == 'GET'
            assert '127.0.0.1' in request.url

            if lock.locked():
                lock.release()
        except AssertionError as e:
            exceptions.append(e)

    lock = Lock()
    exceptions = []
    headers_window.events.request_sent += on_request
    run_test(webview, headers_window, request_test, (exceptions, lock))


def test_request_headers(headers_window):
    def modify_request_headers(request):
        request.headers['Pywebview'] = 'test'

    headers_window.events.request_sent += modify_request_headers
    run_test(webview, headers_window, headers_test)


def request_test(window, exceptions, lock):
    lock.acquire()
    if len(exceptions) > 0:
        raise exceptions[0]


def headers_test(window):
    window.events.loaded.wait()
    headers = window.evaluate_js('document.body.innerText')
    assert 'Pywebview: test' in headers, f'Expected header not found: {headers}'
