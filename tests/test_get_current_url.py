import webview
from .util import run_test

def test_current_url():
    window = webview.create_window('Get Current URL test', 'https://example.org')
    run_test(webview, window, current_url_test, destroy_delay=5)


def test_no_url():
    window = webview.create_window('Get Current URL test')
    run_test(webview, window, no_url_test)


def current_url_test(window):
    assert window.get_current_url() == 'https://example.org/'

def no_url_test(window):
    assert window.get_current_url() is None

