import webview
from .util import run_test


def test_toggle_fullscreen():
    run_test(webview, main_func, toggle_fullscreen)


def main_func():
    webview.create_window('Toggle fullscreen test', 'https://www.example.org')


def toggle_fullscreen():
    webview.toggle_fullscreen()




