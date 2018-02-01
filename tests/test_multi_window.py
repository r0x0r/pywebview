import pytest
import threading
from .util import run_test, destroy_window


def test_bg_color():
    run_test(bg_color)


def test_load_html():
    run_test(load_html)


def test_load_url():
    run_test(load_url)


def test_evaluate_js():
    run_test(evaluate_js)


def bg_color():
    import webview

    def _bg_color(webview):
        child_window = webview.create_window('Window #2', background_color='#0000FF')
        destroy_event.set()

    t = threading.Thread(target=_bg_color, args=(webview,))
    t.start()
    destroy_event = destroy_window(webview, 5)

    webview.create_window('Multi-window background test', 'https://www.example.org')


def evaluate_js():
    import webview

    def _evaluate_js(webview):
        child_window = webview.create_window('Window #2', 'https://google.com')
        result1 = webview.evaluate_js("""
            document.body.style.backgroundColor = '#212121';
            // comment
            function test() {
                return 2 + 5;
            }
            test();
        """)

        assert result1 == 7

        result2 = webview.evaluate_js("""
            document.body.style.backgroundColor = '#212121';
            // comment
            function test() {
                return 2 + 2;
            }
            test();
        """, uid=child_window)
        assert result2 == 4
        destroy_event.set()

    t = threading.Thread(target=_evaluate_js, args=(webview,))
    t.start()
    destroy_event = destroy_window(webview)
    webview.create_window('Multi-window evaluate JS test', 'https://www.example.org')


def load_html():
    import webview

    def _load_html(webview):
        child_window = webview.create_window('Window #2')
        webview.load_html('<body style="background: red;"><h1>Master Window</h1></body>', uid=child_window)
        destroy_event.set()

    t = threading.Thread(target=_load_html, args=(webview,))
    t.start()
    destroy_event = destroy_window(webview)

    webview.create_window('Multi-window load html test', 'https://www.example.org')


def load_url():
    import webview

    def _load_url(webview):
        child_window = webview.create_window('Window #2')
        webview.load_url('https://google.com', uid=child_window)
        destroy_event.set()

    t = threading.Thread(target=_load_url, args=(webview,))
    t.start()
    destroy_event = destroy_window(webview)

    webview.create_window('Multi-window load url test', 'https://www.example.org')


