from threading import Lock
from time import sleep

import webview

from .util import run_test, wait_release


def test_xy():
    window = webview.create_window('xy test', x=200, y=200, width=100, height=100)
    run_test(webview, window, xy)


def test_move_window():
    window = webview.create_window('Move window test', x=200, y=200, width=100, height=100)
    run_test(webview, window, move_window)


def test_move_window_screen_coordinates():
    window = webview.create_window('Move screen coordinates test', x=50, y=50, width=600, height=400)
    run_test(webview, window, move_window_screen_coordinates)


def test_resize_move_window_screen_coordinates():
    window = webview.create_window('Resize and move coordinates test', x=50, y=50, width=700, height=500)
    run_test(webview, window, resize_and_move_window_screen_coordinates)


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


def move_window_screen_coordinates(window):
    # Validate that move() and reported x/y use the same coordinate space
    # regardless of display scaling and monitor resolution.
    screen = webview.screens[0]
    padding = 120

    target_x = max(screen.x, screen.x + screen.width - window.width - padding)
    target_y = max(screen.y, screen.y + screen.height - window.height - padding)

    lock = Lock()
    exception = False

    def moved():
        nonlocal exception
        try:
            # Coordinates are not always exact due to window manager decorations.
            assert abs(window.x - target_x) < 12
            assert abs(window.y - target_y) < 12
        except Exception as e:
            exception = e

        wait_release(lock)

    window.events.moved += moved
    window.move(target_x, target_y)

    assert lock.acquire(3)
    if exception:
        raise exception


def resize_and_move_window_screen_coordinates(window):
    # Resize first and then move to verify that width/height and x/y remain
    # consistent in one coordinate system under DPI scaling.
    screen = webview.screens[0]

    new_width = max(320, min(700, screen.width // 2))
    new_height = max(240, min(520, screen.height // 2))
    window.resize(new_width, new_height)

    # Allow GUI backend to process size update before calculating target coordinates.
    sleep(0.2)

    padding = 40
    target_x = max(screen.x, screen.x + screen.width - window.width - padding)
    target_y = max(screen.y, screen.y + screen.height - window.height - padding)

    lock = Lock()
    exception = False

    def moved():
        nonlocal exception
        try:
            assert abs(window.x - target_x) < 12
            assert abs(window.y - target_y) < 12

            right_edge = window.x + window.width
            bottom_edge = window.y + window.height
            assert right_edge <= screen.x + screen.width + 12
            assert bottom_edge <= screen.y + screen.height + 12
        except Exception as e:
            exception = e

        wait_release(lock)

    window.events.moved += moved
    window.move(target_x, target_y)

    assert lock.acquire(3)
    if exception:
        raise exception
