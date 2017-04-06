import pytest
import threading
from .util import run_test, destroy_window


def load_html():
    import webview

    def _load_html(webview):
        webview.load_html('<h1>This is dynamically loaded HTML</h1>')

    t = threading.Thread(target=_load_html, args=(webview,))
    t.start()
    destroy_window(webview)

    webview.create_window('', 'https://www.example.org')


def test_load_html():
    run_test(load_html)
