import webview
from .util import run_test
from time import sleep


def test_resize():
    window = webview.create_window('Set Window Size Test', 'https://www.example.org', width=800, height=600)
    run_test(webview, window, resize)


def resize(window):
    assert window.width == 800
    assert window.height == 600

    window.resize(500, 500)

    sleep(0.5)

    assert window.width == 500
    assert window.height == 500
