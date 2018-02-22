import math
import threading
from .util import run_test, run_test2, destroy_window
import webview
import pytest


def main_func():
    webview.create_window('Evaluate JS test', 'https://www.example.org')


def test_mixed():
    def thread_func():
        result = webview.evaluate_js("""
            document.body.style.backgroundColor = '#212121';
            // comment
            function test() {
                return 2 + 2;
            }
            test();
        """)
        assert result == 4

    run_test2(main_func, thread_func, webview)


def test_array():
    def thread_func():
        result = webview.evaluate_js("""
        function getValue() { 
            return [undefined, 1, 'two', 3.00001, {four: true}]
        }

        getValue()
        """)
        assert result == [None, 1, 'two', 3.00001, {'four': True}]

    run_test2(main_func, thread_func, webview)


def test_object():
    def thread_func():
        result = webview.evaluate_js("""
        function getValue() { 
            return {1: 2, 'test': true, obj: {2: false, 3: 3.1}}
        }

        getValue()
        """)
        assert result == {'1': 2, 'test': True, 'obj': {'2': False, '3': 3.1}}


    run_test2(main_func, thread_func, webview)


def test_string():
    def thread_func():
        result = webview.evaluate_js("""
        function getValue() { 
            return "this is only a test"
        }

        getValue()
        """)
        assert result == u'this is only a test'

    run_test2(main_func, thread_func, webview)


def test_int():
    def thread_func():
        result = webview.evaluate_js("""
        function getValue() { 
            return 23
        }

        getValue()
        """)
        assert result == 23

    run_test2(main_func, thread_func, webview)


def test_float():
    def thread_func():
        result = webview.evaluate_js("""
        function getValue() { 
            return 23.23443
        }

        getValue()
        """)
        assert result == 23.23443

    run_test2(main_func, thread_func, webview)


def test_undefined():
    def thread_func():
        result = webview.evaluate_js("""
        function getValue() { 
            return undefined
        }

        getValue()
        """)
        assert result is None

    run_test2(main_func, thread_func, webview)


def test_null():
    def thread_func():
        result = webview.evaluate_js("""
        function getValue() { 
            return null
        }

        getValue()
        """)
        assert result is None

    run_test2(main_func, thread_func, webview)


def test_nan():
    def thread_func():
        result = webview.evaluate_js("""
        function getValue() { 
            return NaN
        }

        getValue()
        """)
        assert math.isnan(result)

    run_test2(main_func, thread_func, webview)