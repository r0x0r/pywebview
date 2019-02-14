import webview
from .util import run_test


def test_min_size():
    run_test(webview, frameless)


def frameless():
    webview.create_window('Frameless test', 'https://www.example.org', frameless=True)


