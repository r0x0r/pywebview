import pytest
import threading
from .util import run_test, destroy_window



def open_file_dialog():
    import webview

    def _open_file_dialog(webview):
        webview.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=True)

    t = threading.Thread(target=_open_file_dialog, args=(webview,))
    t.start()
    destroy_window(webview, 5)

    webview.create_window('', 'https://www.example.org')


def test_open_file_dialog():
    run_test(open_file_dialog)
