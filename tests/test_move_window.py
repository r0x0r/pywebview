from time import sleep
import pytest
import webview

from .util import run_test

def test_xy():
    window = webview.create_window('xy test', x=200, y=200, width=100, height=100)
    run_test(webview, window, xy)


def test_move_window():
    window = webview.create_window('Move window test', x=200, y=200, width=100, height=100)
    run_test(webview, window, move_window)


def xy(window):
    # Coordinates are not always exact due to window manager decorations
    assert abs(window.x - 200) < 10
    assert abs(window.y - 200) < 10


def move_window(window):
    # Coordinates are not always exact due to window manager decorations
    window.move(300, 300)
    sleep(1)

    assert abs(window.x - 300) < 10
    assert abs(window.y - 300) < 10
