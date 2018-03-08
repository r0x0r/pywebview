import webview
from .util import run_test2


def main_func():
    webview.create_window('Evaluate JS test', 'https://example.org')


def current_url_test():
    assert webview.get_current_url() == 'https://example.org/'


def test_current_url():
    run_test2(main_func, current_url_test, webview)