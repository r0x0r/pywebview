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


# tests/test_get_current_url.py can't be reused: it navigates to example.org,
# which needs the network, and its second case asserts None for a window with no
# URL - on Android there is no such window, since one is always loaded with
# either a URL or html=.
def test_current_url():
    window = webview.create_window('Window test', app)
    run_test(webview, window, current_url_test)


def size_test(window):
    # Android windows are whatever size the activity is, so there is nothing to
    # compare against - only that the WebView has been laid out.
    assert window.width > 0, f'width was {window.width}'
    assert window.height > 0, f'height was {window.height}'


def current_url_test(window):
    # Served over HTTP rather than loaded with html=: loadDataWithBaseURL with a
    # null base URL leaves the WebView reporting about:blank.
    url = window.get_current_url()
    assert url is not None and '127.0.0.1' in url, url
