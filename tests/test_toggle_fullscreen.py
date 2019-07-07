import webview
from .util import run_test


def test_toggle_fullscreen():
    window = webview.create_window('Toggle fullscreen test', 'https://www.example.org')
    run_test(webview, window, toggle_fullscreen)


def toggle_fullscreen(window):
    window.toggle_fullscreen()




