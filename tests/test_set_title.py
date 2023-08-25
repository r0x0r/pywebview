import webview

from .util import run_test

_new_title = "New title"


def test_set_title():
    window = webview.create_window("Set title test", html="https://www.example.org")
    run_test(webview, window, set_title)


def set_title(window):
    window.set_title(_new_title)
    assert all(
        [
            window.title == _new_title,
            webview.windows[0].title == _new_title,
            webview.active_window().title == _new_title,
        ]
    )
