import threading
from .util import run_test
import webview


def test_mixed():
    run_test(webview, main_func, mixed_test)


def test_array():
    run_test(webview, main_func, array_test)


def test_object():
    run_test(webview, main_func, object_test)


def test_string():
    run_test(webview, main_func, string_test)


def test_int():
    run_test(webview, main_func, int_test)


def test_float():
    run_test(webview, main_func, float_test)


def test_undefined():
    run_test(webview, main_func, undefined_test)


def test_null():
    run_test(webview, main_func, null_test)


def test_nan():
    run_test(webview, main_func, nan_test)


def main_func():
    def load_html():
        webview.load_html('<h1>test</h1>')

    t = threading.Thread(target=load_html)
    t.start()
    webview.create_window('Evaluate JS test')


def mixed_test():
    result = webview.evaluate_js("""
        document.body.style.backgroundColor = '#212121';
        // comment
        function test() {
            return 2 + 2;
        }
        test();
    """)
    assert result == 4


def array_test():
    result = webview.evaluate_js("""
    function getValue() {
        return [undefined, 1, 'two', 3.00001, {four: true}]
    }

    getValue()
    """)
    assert result == [None, 1, 'two', 3.00001, {'four': True}]


def object_test():
    result = webview.evaluate_js("""
    function getValue() {
        return {1: 2, 'test': true, obj: {2: false, 3: 3.1}}
    }

    getValue()
    """)
    assert result == {'1': 2, 'test': True, 'obj': {'2': False, '3': 3.1}}


def string_test():
    result = webview.evaluate_js("""
    function getValue() {
        return "this is only a test"
    }

    getValue()
    """)
    assert result == u'this is only a test'


def int_test():
    result = webview.evaluate_js("""
    function getValue() {
        return 23
    }

    getValue()
    """)
    assert result == 23


def float_test():
    result = webview.evaluate_js("""
    function getValue() {
        return 23.23443
    }

    getValue()
    """)
    assert result == 23.23443


def undefined_test():
    result = webview.evaluate_js("""
    function getValue() {
        return undefined
    }

    getValue()
    """)
    assert result is None


def null_test():
    result = webview.evaluate_js("""
    function getValue() {
        return null
    }

    getValue()
    """)
    assert result is None


def nan_test():
    result = webview.evaluate_js("""
    function getValue() {
        return NaN
    }

    getValue()
    """)
    assert result is None
