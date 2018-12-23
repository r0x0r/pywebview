import webview
from .util import run_test


def test_fullscreen():
    run_test(webview, fullscreen)


def fullscreen():
    webview.create_window('Fullscreen test', 'https://www.example.org', fullscreen=True)



