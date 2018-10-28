import webview
from .util import run_test


def test_minimized():
    run_test(minimized)


def minimized():
    webview.create_window('Min size test', 'https://www.example.org',
                          width=800, height=600, minimized=True)


