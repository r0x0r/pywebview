import webview
from .util import run_test


def test_url_load():
    run_test(webview, main_func, url_load)


def main_func():
    webview.create_window('URL change test', 'https://www.example.org')


def url_load():
    webview.load_url('https://www.google.org')



