import webview
from .util import run_test, assert_js


def test_bg_color():
    run_test(webview, main_func, bg_color)


def test_load_html():
    run_test(webview, main_func, load_html)


def test_load_url():
    run_test(webview, main_func, load_url)


def test_evaluate_js():
    run_test(webview, main_func, evaluate_js)


def test_js_bridge():
    run_test(webview, main_api_func, js_bridge)


def main_func():
    webview.create_window('Multi-window test', 'https://www.example.org')


def main_api_func():
    class Api1:
        def test1(self, params):
            return 1

    webview.create_window('Multi-window js bridge test', 'https://www.example.org', js_api=Api1())


def bg_color():
    child_window = webview.create_window('Window #2', background_color='#0000FF')
    assert child_window != 'MainWindow'
    webview.webview_ready()
    webview.destroy_window(child_window)


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



