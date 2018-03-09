import webview
import pytest
from .util import run_test


def test_bg_color():
    run_test(webview, bg_color)


def test_invalid_bg_color():
    run_test(webview, invalid_bg_color)


def bg_color():
    webview.create_window('Background color test', 'https://www.example.org', background_color='#0000FF')


def invalid_bg_color():
    with pytest.raises(ValueError):
        webview.create_window('Background color test', 'https://www.example.org', background_color='#dsg0000FF')

    with pytest.raises(ValueError):
        webview.create_window('Background color test', 'https://www.example.org', background_color='FF00FF')

    with pytest.raises(ValueError):
        webview.create_window('Background color test', 'https://www.example.org', background_color='#ac')

    with pytest.raises(ValueError):
        webview.create_window('Background color test', 'https://www.example.org', background_color='#EFEFEH')

    with pytest.raises(ValueError):
        webview.create_window('Background color test', 'https://www.example.org', background_color='#0000000')


