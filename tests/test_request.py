import time
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
    lock.acquire()
    headers_window.events.request_sent += on_request
    run_test(webview, headers_window, request_test, (exceptions, lock))


def test_request_headers(headers_window):
    def modify_request_headers(request):
        request.headers['Pywebview'] = 'test'

    headers_window.events.request_sent += modify_request_headers
    run_test(webview, headers_window, headers_test)


def test_request_cancel():
    app = Bottle()
    hits = []
    cancelled = []

    @app.route('/')
    def index():
        return 'index'

    @app.route('/blocked')
    @app.route('/allowed')
    def page():
        name = request.path.strip('/')
        hits.append(name)
        return name

    def cancel_blocked(request):
        if request.url.endswith('/blocked'):
            cancelled.append(request.url)
            return False

    window = webview.create_window('Cancel test', app)
    window.events.request_sent += cancel_blocked
    run_test(webview, window, cancel_test, (hits, cancelled))


def request_test(window, exceptions, lock):
    assert lock.acquire(timeout=10)
    if len(exceptions) > 0:
        raise exceptions[0]


def headers_test(window):
    window.events.loaded.wait()
    headers = window.evaluate_js('document.body.innerText')
    assert 'Pywebview: test' in headers, f'Expected header not found: {headers}'


def cancel_test(window, hits, cancelled):
    window.events.loaded.wait()
    url = window.get_current_url().rstrip('/')
    window.load_url(url + '/blocked')
    time.sleep(2)
    assert cancelled == [url + '/blocked'], f'request_sent did not see the request: {cancelled}'
    # The current page stays usable
    assert window.evaluate_js('document.body.innerText') == 'index'

    # A request that is not cancelled reaches the server
    window.load_url(url + '/allowed')
    assert window.events.loaded.wait(10), 'Allowed page did not load'
    assert hits == ['allowed'], f'Unexpected server hits: {hits}'
