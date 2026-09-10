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
    # test_cookies.py's desktop fixture can't be reused verbatim: it asserts on
    # `Set-Cookie: pywebview=true; Domain=127.0.0.1;`, but Android's get_cookies()
    # fills the domain from urlparse(current_url).netloc, which carries the port
    # too, so that prefix never matches. The embedded Bottle app also gives a real
    # Set-Cookie response header rather than relying on assets/script.js setting
    # document.cookie, mirroring what tests/android/main.py already does.
    return webview.create_window('Cookie test', app)


# Matches how tests/android/main.py starts, and for the same two reasons.
#
# private_mode (webview.start's default) makes the Android backend call
# CookieManager.setAcceptCookie(False) on page finished, so cookies would be
# silently dropped.
#
# ssl is needed because Android blocks cleartext HTTP by default
# (usesCleartextTraffic is false for targetSdk >= 28), so the local Bottle
# server this test runs against has to be served over https or the page never
# loads. pywebview generates a self-signed cert for it, which the Android
# backend accepts because _state['ssl'] also turns on the client's
# ignore-ssl-errors flag. The other test modules load their content with html=,
# which never goes over the network, so only this one needs either flag.
COOKIE_START_ARGS = {'private_mode': False, 'ssl': True}


def test_get_cookies(window):
    run_test(webview, window, get_cookies_test, start_args=COOKIE_START_ARGS)


def test_clear_cookies(window):
    run_test(webview, window, clear_cookies_test, start_args=COOKIE_START_ARGS)


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
