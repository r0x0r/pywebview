import pytest
import webview
from .util import destroy_window, run_test

def bg_color():
    import webview
    destroy_window(webview)
    webview.create_window('Background color test', 'https://www.example.org', bg_color='#0000FF')


def test_bg_color():
    run_test(bg_color)
