import pytest
import threading
from .util import run_test, destroy_window


def no_resize():
    import webview

    def _no_resize(webview):
        assert webview.webview_ready(10)
        destroy_event.set()

    t = threading.Thread(target=_no_resize, args=(webview,))
    t.start()
    destroy_event = destroy_window(webview)
    webview.create_window('Min size test', 'https://www.example.org',
                          width=800, height=600, resizable=True, min_size=(400, 200))


def test_noresize():
    run_test(no_resize)
