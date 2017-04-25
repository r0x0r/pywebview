import pytest
import sys
from .util import run_test, destroy_window


def simple_browser():
    import webview
    destroy_window(webview, 0)
    webview.create_window('', 'https://www.example.org')


def test_simple_browser():
    run_test(simple_browser)


if __name__ == '__main__':
    pytest.main()
