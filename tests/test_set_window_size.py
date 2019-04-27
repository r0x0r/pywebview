import webview
from .util import run_test


def test_set_window_size():
    window = webview.create_window('Set Window Size Test', 'https://www.example.org')
    run_test(webview, window, set_window_size)


def set_window_size(window):
    window.set_window_size(500, 500)
