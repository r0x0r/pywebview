from threading import Lock
from time import sleep
import pytest
import webview

from .util import run_test, wait_release

def test_xy():
    window = webview.create_window('xy test', x=200, y=200, width=100, height=100)
    run_test(webview, window, xy)


def test_move_window():
    window = webview.create_window('Move window test', x=200, y=200, width=100, height=100)
    run_test(webview, window, move_window)


def xy(window):
    # Coordinates are not always exact due to window manager decorations
    window.events.shown.wait()
    assert abs(window.x - 200) < 10
    assert abs(window.y - 200) < 10


def move_window(window):
    # Coordinates are not always exact due to window manager decorations
    def moved():
        try:
            assert abs(window.x - 300) < 10
            assert abs(window.y - 300) < 10
        except AssertionError as e:
            nonlocal exception
            exception = e

        wait_release(lock)

    lock = Lock()
    exception = False
    window.events.moved += moved
    window.move(300, 300)

    assert lock.acquire(3)
    if exception:
        raise exception

