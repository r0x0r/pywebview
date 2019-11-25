import pytest
import webview
from .util import run_test, assert_js

@pytest.fixture
def window():
    return webview.create_window('Main window', html='<html><body><h1>Master window</h1></body></html>')


def test_bg_color():
    window = webview.create_window('Main window', background_color='#0000FF')

    run_test(webview, window, bg_color)


def test_load_html(window):
    run_test(webview, window, load_html)


def test_load_url(window):
    run_test(webview, window, load_url)


def test_evaluate_js(window):
    run_test(webview, window, evaluate_js)

def test_js_bridge():
    class Api1:
        def test1(self):
            return 1

    window = webview.create_window('Multi-window js bridge test', html='<html><body><h1>Master window</h1></body></html>', js_api=Api1())
    run_test(webview, window, js_bridge)


def bg_color(window):
    child_window = webview.create_window('Window #2', background_color='#0000FF')

    assert child_window.uid != 'MainWindow'
    child_window.destroy()


def js_bridge(window):
    class Api2:
        def test2(self):
            return 2

    api2 = Api2()
    child_window = webview.create_window('Window #2', js_api=api2)
    assert child_window.uid != 'MainWindow'
    child_window.load_html('<html><body><h1>Secondary window</h1></body></html>')
    assert_js(window, 'test1', 1)
    assert_js(child_window, 'test2', 2)

    child_window.destroy()


def evaluate_js(window):
    child_window = webview.create_window('Window #2', 'https://google.com')
    assert child_window.uid != 'MainWindow'
    result1 = window.evaluate_js("""
        document.body.style.backgroundColor = '#212121';
        // comment
        function test() {
            return 2 + 5;
        }
        test();
    """)

    assert result1 == 7

    result2 = child_window.evaluate_js("""
        document.body.style.backgroundColor = '#212121';
        // comment
        function test() {
            return 2 + 2;
        }
        test();
    """)
    assert result2 == 4
    child_window.destroy()


def load_html(window):
    child_window = webview.create_window('Window #2', html='<body style="background: red;"><h1>Master Window</h1></body>')
    assert child_window != 'MainWindow'
    child_window.destroy()


def load_url(window):
    child_window = webview.create_window('Window #2')
    assert child_window != 'MainWindow'
    child_window.load_url('https://google.com')
    child_window.destroy()



