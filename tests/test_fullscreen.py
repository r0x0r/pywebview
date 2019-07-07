import webview
from .util import run_test


def test_fullscreen():
    window = webview.create_window('Fullscreen test', 'https://www.example.org', fullscreen=True)
    run_test(webview, window)



