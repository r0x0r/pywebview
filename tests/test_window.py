import webview
from .util import run_test


def test_window_count():
    window = webview.create_window('Window object test')
    run_test(webview, window, window_count)


def window_count(window):
    assert len(webview.windows) == 1



