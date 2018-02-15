import threading
import pytest
from .util import destroy_window, run_test


def bg_color():
    import webview

    def _bg_color(webview):
        assert webview.webview_ready(10)
        destroy_event.set()

    t = threading.Thread(target=_bg_color, args=(webview,))
    t.start()
    destroy_event = destroy_window(webview)
    webview.create_window('Background color test', 'https://www.example.org', background_color='#0000FF')


def invalid_bg_color():
    import webview

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


def test_bg_color():
    run_test(bg_color)


def test_invalid_bg_color():
    run_test(invalid_bg_color)
