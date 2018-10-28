import webview
from .util import run_test


def test_min_size():
    run_test(min_size)


def min_size():
    webview.create_window('Min size test', 'https://www.example.org',
                          width=800, height=600, minimized=True)


