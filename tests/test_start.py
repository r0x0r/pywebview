import os
from time import sleep
from .util import run_test, assert_js
import webview


class Api:
    def test(self, params):
        return 'JS Api is working too'


def test_start():
    run_test(webview, main_func, assert_func)


def main_func():
    api = Api()
    webview.create_window('Relative URL test', 'assets/test.html', debug=True, js_api=api)


def assert_func():
    sleep(1)
    html_result = webview.evaluate_js('document.getElementById("heading").innerText')
    assert html_result == 'Hello there!'

    css_result = webview.evaluate_js('window.getComputedStyle(document.body, null).getPropertyValue("background-color")')
    assert css_result == 'rgb(255, 0, 0)'

    js_result = webview.evaluate_js('window.testResult')
    assert js_result == 80085

    assert_js(webview, 'test', 'JS Api is working too')




