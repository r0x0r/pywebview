import webview
import pytest
from .util import run_test


def test_bg_color():
    window = webview.create_window('Background color test', 'https://www.example.org', background_color='#0000FF')
    run_test(webview, window)


def test_invalid_bg_color():
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



