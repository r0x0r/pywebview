import pytest
import webview
from .util import run_test, assert_js

@pytest.fixture
def window():
    class Api1:
        def test1(self, params):
            return 1

    return webview.create_window('Multi-window js bridge test', 'https://www.example.org', js_api=Api1())


def test_bg_color(window):
    child_window = webview.create_window('Window #2', background_color='#0000FF')

    run_test(webview, window, bg_color)


def test_load_html(window):
    run_test(webview, window, load_html)


def test_load_url(window):
    run_test(webview, window, load_url)


def test_evaluate_js(window):
    run_test(webview, window, evaluate_js)


def test_js_bridge(window):
    run_test(webview, window, js_bridge)


def bg_color(window):
    assert child_window != 'MainWindow'
    window.destroy_window(child_window)


def js_bridge():
    class Api2:
        def test2(self, params):
            return 2

    webview.load_html('<html><body><h1>Master window</h1></body></html>')

    api2 = Api2()
    child_window = webview.create_window('Window #2', js_api=api2)
    assert child_window != 'MainWindow'
    webview.load_html('<html><body><h1>Secondary window</h1></body></html>', uid=child_window)
    assert_js(webview, 'test1', 1)
    assert_js(webview, 'test2', 2, uid=child_window)

    webview.destroy_window(child_window)


def evaluate_js():
    child_window = webview.create_window('Window #2', 'https://google.com')
    assert child_window != 'MainWindow'
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


def load_html():
    child_window = webview.create_window('Window #2')
    assert child_window != 'MainWindow'
    webview.load_html('<body style="background: red;"><h1>Master Window</h1></body>', uid=child_window)
    webview.destroy_window(child_window)


def load_url():
    child_window = webview.create_window('Window #2')
    assert child_window != 'MainWindow'
    webview.load_url('https://google.com', uid=child_window)
    webview.destroy_window(child_window)



