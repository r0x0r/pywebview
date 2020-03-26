import webview
from .util import run_test


def test_on_top():
    window = webview.create_window("Toggle on_top test", "https://www.example.org")
    run_test(webview, window, on_top)


def on_top(window):
    try:
        window.on_top = True
        window.on_top = False
    except NotImplementedError:
        print('This OS/guilib does not yet have "on_top" feature.')
