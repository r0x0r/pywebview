from bottle import Bottle

import webview

from .util import run_test

HTML = '<html><body>window test</body></html>'

app = Bottle()


@app.route('/')
def index():
    return HTML


def test_window_size():
    window = webview.create_window('Window test', html=HTML)
    run_test(webview, window, size_test)


# Unlike tests/test_get_current_url.py, no network and no URL-less window: on
# Android a window is always loaded with either a URL or html=.
def test_current_url():
    window = webview.create_window('Window test', app)
    run_test(webview, window, current_url_test)


def size_test(window):
    # Android windows are whatever size the activity is, so only that the
    # WebView has been laid out can be asserted.
    assert window.width > 0, f'width was {window.width}'
    assert window.height > 0, f'height was {window.height}'


def current_url_test(window):
    # Served over HTTP rather than html=: loadDataWithBaseURL with a null base
    # URL leaves the WebView reporting about:blank.
    url = window.get_current_url()
    assert url is not None and '127.0.0.1' in url, url
