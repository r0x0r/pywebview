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
    #
    # Private mode is what switches cookies off, and passing private_mode=False
    # to webview.start() is not enough to turn them back on: conftest reloads the
    # webview module between tests, which rebinds webview._state to a fresh dict
    # while the already-imported backend holds on to the old one. Set it where
    # the backend actually reads it.
    from webview.platforms import android

    android._state['private_mode'] = False
    yield webview.create_window('Cookie test', app)
    android._state['private_mode'] = True


# The other test modules load their content with html=, which never goes over
# the network, so only this one needs a non-private window.
#
# No ssl=True, unlike tests/android/main.py: that needs cryptography, whose Rust
# extension cannot be loaded by p4a's Python 3.14 (see buildozer.spec). Cleartext
# HTTP is granted through the manifest instead, so plain http works here.
COOKIE_START_ARGS = {'private_mode': False}


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
