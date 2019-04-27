import webview
from .util import run_test


def test_set_title():
    window = webview.create_window('Set title test', 'https://www.example.org')
    run_test(webview, window, set_title)


def set_title(window):
    window.set_title('New title')

