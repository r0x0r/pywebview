import pytest
import threading
from .util import run_test, destroy_window


def toggle_fullscreen():
    import webview

    def _toggle_fullscreen(webview):
        webview.toggle_fullscreen()

    t = threading.Thread(target=_toggle_fullscreen, args=(webview,))
    t.start()
    destroy_window(webview)

    webview.create_window('', 'https://www.example.org')


def test_toggle_fullscreen():
    run_test(toggle_fullscreen)
