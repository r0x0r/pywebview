import pytest
from bottle import Bottle, response

import webview

from .util import run_test

app = Bottle()


@app.route('/')
def index():
    response.set_cookie('pywebview', 'true', path='/')
    return '<html><body>cookie test</body></html>'


@pytest.fixture
def window():
    # test_cookies.py's desktop fixture points at a static asset served over
    # file://, which never gets a real Set-Cookie response header. Android's
    # WebView needs an actual HTTP response to exercise get_cookies/clear_cookies,
    # so this mirrors the embedded-Bottle-server pattern tests/android/main.py
    # already uses to serve the manual test suite.
    return webview.create_window('Cookie test', app)


def test_get_cookies(window):
    run_test(webview, window, get_cookies_test)


def test_clear_cookies(window):
    run_test(webview, window, clear_cookies_test)


def get_cookies_test(window):
    cookies = window.get_cookies()
    assert len(cookies) == 1
    # get_cookies() returns a list of SimpleCookie-like dicts keyed by cookie
    # name (see webview/platforms/android/__init__.py:get_cookies), not Morsels
    # directly, so index into the dict rather than reading .key/.value.
    assert 'pywebview' in cookies[0]
    assert cookies[0]['pywebview'].value == 'true'


def clear_cookies_test(window):
    window.clear_cookies()
    cookies = window.get_cookies()
    assert len(cookies) == 0
