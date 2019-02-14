import webview
from .util import run_test


def test_set_title():
    run_test(webview, main_func, set_title)


def main_func():
    webview.create_window('Set title test', 'https://www.example.org')


def set_title():
    webview.set_title('New title')

