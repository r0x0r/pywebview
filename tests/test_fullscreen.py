import pytest
import webview
from .util import destroy_window, run_test

def fullscreen():
    import webview
    destroy_window(webview, 0)
    webview.create_window('', 'https://www.example.org', fullscreen=True)


def test_simple_browser():
    run_test(fullscreen)
