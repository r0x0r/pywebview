import webview
from .util import run_test


def test_xy():
    window = webview.create_window('xy test', x=0, y=0)
    run_test(webview, window)


def test_move_window():
    window = webview.create_window('Move window test', x=0, y=0)
    run_test(webview, window, move_window)

def move_window(window):
    window.move(100, 100)


