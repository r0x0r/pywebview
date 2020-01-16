import webview
from .util import run_test
from time import sleep

def test_xy():
    window = webview.create_window('xy test', x=0, y=0)
    run_test(webview, window, xy)


def test_move_window():
    window = webview.create_window('Move window test', x=0, y=0)
    run_test(webview, window, move_window)


def xy(window):
    assert window.x == 0
    assert window.y == 0


def move_window(window):
    window.move(100, 100)
    # On Cocoa resize is done asynchronously, so we have to delay until retrieve new coordinatesß
    sleep(0.5)

    assert window.x == 100
    assert window.y == 100


