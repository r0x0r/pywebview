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




def test_json_to_dict():
    def thread_func():
        result = webview.evaluate_js("""
        function get_obj() { 
            return {1: 2, 'test': true, obj: {2: false, 3: 'yes'}}
        }

        get_obj()
        """)
        assert result == {'1': 2, 'test': True, 'obj': {2: False, 3: 3.1}} # 1 is converted to '1' on OSX

    run_test2(main_func, thread_func, webview)

#def test_string():
#    run_test(string_test)

#def test_int():
#    run_test(int_test)