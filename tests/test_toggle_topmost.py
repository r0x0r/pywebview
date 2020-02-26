import webview
from .util import run_test


def test_toggle_topmost():
    window = webview.create_window("Toggle topmost test", "https://www.example.org")
    run_test(webview, window, toggle_topmost)


def toggle_topmost(window):
    try:
        window.toggle_topmost()
    except NotImplementedError:
        print('This OS/guilib does not yet have "topmost" feature.')
