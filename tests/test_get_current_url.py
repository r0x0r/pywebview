import webview
from .util import run_test



def test_current_url():
    run_test(main_func, current_url_test)


def test_no_url():
    run_test(no_url_func, no_url_test)


def main_func():
    webview.create_window('Evaluate JS test', 'https://example.org')


def no_url_func():
    webview.create_window('Evaluate JS test')


def current_url_test():
    assert webview.get_current_url() == 'https://example.org/'


def no_url_test():
    assert webview.get_current_url() is None

