import webview
from .util import run_test


def test_simple_browser():
    run_test(main_func)


def main_func():
    webview.create_window('Simple browser test', 'https://www.example.org')

