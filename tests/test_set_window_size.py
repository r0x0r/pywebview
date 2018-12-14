import webview
from .util import run_test


def test_set_window_size():
    run_test(main_func, set_window_size)


def main_func():
    webview.create_window('Set Window Size Test', 'https://www.example.org')


def set_window_size():
    webview.set_window_size(500, 500)
