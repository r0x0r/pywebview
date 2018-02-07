import pytest
import threading
from .util import run_test, destroy_window, assert_js


def test_bg_color():
    run_test(bg_color)


def test_load_html():
    run_test(load_html)


def test_load_url():
    run_test(load_url)


def test_evaluate_js():
    run_test(evaluate_js)


def test_js_bridge():
    run_test(js_bridge)


def bg_color():
    import webview

    def _bg_color(webview):
        child_window = webview.create_window('Window #2', background_color='#0000FF')
        webview.webview_ready()
        webview.destroy_window(child_window)
        destroy_event.set()

    t = threading.Thread(target=_bg_color, args=(webview,))
    t.start()
    destroy_event = destroy_window(webview, 5)

    webview.create_window('Multi-window background test', 'https://www.example.org')



def js_bridge():
    import webview

    class Api1:
        def test1(self, params):
            return 1

    class Api2:
        def test2(self, params):
            return 2

    def _js_bridge(webview):
        webview.load_html('<html><body><h1>Master window</h1></body></html>')

        api2 = Api2()
        child_window = webview.create_window('Window #2', js_api=api2)
        webview.load_html('<html><body><h1>Secondary window</h1></body></html>', uid=child_window)

        assert_js(webview, 'test1', 1)
        assert_js(webview, 'test2', 2, uid=child_window)

        webview.destroy_window(child_window)
        destroy_event.set()

    t = threading.Thread(target=_js_bridge, args=(webview,))
    t.start()
    destroy_event = destroy_window(webview)

    api1 = Api1()
    webview.create_window('Multi-window JS bridge test', js_api=api1)


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
        webview.destroy_window(child_window)
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
        webview.destroy_window(child_window)
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
        webview.destroy_window(child_window)
        destroy_event.set()

    t = threading.Thread(target=_load_url, args=(webview,))
    t.start()
    destroy_event = destroy_window(webview)

    webview.create_window('Multi-window load url test', 'https://www.example.org')


