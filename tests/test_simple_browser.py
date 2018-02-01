import pytest

import sys
import threading
from .util import run_test, destroy_window


def simple_browser():
    import webview

    def _simple_browser(webview):
        assert webview.webview_ready(10)
        destroy_event.set()

    t = threading.Thread(target=_simple_browser, args=(webview,))
    t.start()
    destroy_event = destroy_window(webview)
    webview.create_window('Simple browser test', 'https://www.example.org')


def test_simple_browser():
    run_test(simple_browser)


if __name__ == '__main__':
    pytest.main()
