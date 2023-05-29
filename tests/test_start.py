from time import sleep

import webview

from .util import assert_js, run_test


class Api:
    def test(self):
        return 'JS Api is working too'


def test_start():
    api = Api()
    window = webview.create_window('Relative URL test', 'assets/test.html', js_api=api)
    run_test(webview, window, assert_func)


def assert_func(window):
    sleep(1)
    html_result = window.evaluate_js('document.getElementById("heading").innerText')
    assert html_result == 'Hello there!'

    css_result = window.evaluate_js(
        'window.getComputedStyle(document.body, null).getPropertyValue("background-color")'
    )
    assert css_result == 'rgb(255, 0, 0)'

    js_result = window.evaluate_js('window.testResult')
    assert js_result == 80085

    assert_js(window, 'test', 'JS Api is working too')
