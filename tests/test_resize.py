import webview
from .util import run_test


def test_resize():
    window = webview.create_window('Set Window Size Test', 'https://www.example.org')
    run_test(webview, window, resize)


def resize(window):
    window.resize(500, 500)
