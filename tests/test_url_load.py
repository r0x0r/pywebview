import webview
from .util import run_test


def test_url_load():
    window = webview.create_window('URL change test', 'https://www.example.org')
    run_test(webview, window, url_load)


def url_load(window):
    window.load_url('https://www.google.org')



