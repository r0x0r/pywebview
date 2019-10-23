import webview
from .util import run_test


def test_load_html():
    window = webview.create_window('Load HTML test')
    run_test(webview, window, load_html)


def load_html(window):
    window.load_html('<h1>This is dynamically loaded HTML</h1>')


