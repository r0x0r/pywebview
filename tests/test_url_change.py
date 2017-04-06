import pytest
import threading
from .util import run_test, destroy_window


def change_url():
    import webview

    def _change_url(webview):
        webview.change_url('http://www.example.org')

    t = threading.Thread(target=_change_url, args=(webview,))
    t.start()

    destroy_window(webview)
    webview.create_window('', 'https://www.example.org')


def test_change_url():
    run_test(change_url)
