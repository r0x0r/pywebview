import pytest
import threading
from .util import run_test, destroy_window


def no_resize():
    import webview
    destroy_window(webview)
    webview.create_window('No resize test', 'https://www.example.org', resizable=False)


def test_noresize():
    run_test(no_resize)
