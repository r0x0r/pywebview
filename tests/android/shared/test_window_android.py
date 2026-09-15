import webview

from .util import run_test

HTML = '<html><body>window test</body></html>'


# tests/test_get_current_url.py can't be reused: it navigates to example.org,
# which needs the network, and its second case expects None for a window with no
# URL - on Android there is no such window, since one is always loaded with
# either a URL or html=.
def test_window_size():
    window = webview.create_window('Window test', html=HTML)
    run_test(webview, window, size_test)


def test_current_url():
    window = webview.create_window('Window test', html=HTML)
    run_test(webview, window, current_url_test)


def size_test(window):
    width, height = window.get_size()

    # Android windows are whatever size the activity is - there is nothing to
    # compare against, only that the WebView has been laid out.
    assert width > 0, f'width was {width}'
    assert height > 0, f'height was {height}'


def current_url_test(window):
    # html= is loaded through loadDataWithBaseURL with a null base URL, so the
    # WebView reports the data: URL it was given.
    url = window.get_current_url()
    assert url is not None and url.startswith('data:text/html'), url
