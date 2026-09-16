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
    # private_mode=False passed to webview.start() is not enough: conftest
    # reloads the webview module between tests, rebinding webview._state while
    # the already-imported backend holds on to the old dict.
    from webview.platforms import android

    android._state['private_mode'] = False
    yield webview.create_window('Cookie test', app)
    android._state['private_mode'] = True


# No ssl=True: that needs cryptography, which cannot load here (see
# buildozer.spec). Cleartext HTTP is granted through the manifest instead.
COOKIE_START_ARGS = {'private_mode': False}


def test_get_cookies(window):
    run_test(webview, window, get_cookies_test, start_args=COOKIE_START_ARGS)


def test_clear_cookies(window):
    run_test(webview, window, clear_cookies_test, start_args=COOKIE_START_ARGS)


def get_cookies_test(window):
    cookies = window.get_cookies()
    assert len(cookies) == 1
    # get_cookies() returns dicts keyed by cookie name, not Morsels directly.
    assert 'pywebview' in cookies[0]
    assert cookies[0]['pywebview'].value == 'true'


def clear_cookies_test(window):
    window.clear_cookies()
    cookies = window.get_cookies()
    assert len(cookies) == 0
