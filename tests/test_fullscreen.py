import pytest
import webview
from .util import destroy_window, run_test

def fullscreen():
    import webview
    destroy_window(webview)
    webview.create_window('Fullscreen test', 'https://www.example.org', fullscreen=True)


def test_simple_browser():
    run_test(fullscreen)
