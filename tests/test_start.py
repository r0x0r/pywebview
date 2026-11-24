from queue import Queue

import pytest

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
    window.events.loaded.wait()
    html_result = window.evaluate_js('document.getElementById("heading").innerText')
    assert html_result == 'Hello there!'

    css_result = window.evaluate_js(
        'window.getComputedStyle(document.body, null).getPropertyValue("background-color")'
    )
    assert css_result == 'rgb(255, 0, 0)'

    js_result = window.evaluate_js('window.testResult')
    assert js_result == 80085

    assert_js(window, 'test', 'JS Api is working too')


@pytest.mark.parametrize('args, expected', [(None, ()), (5, (5,))])
def test_start_func_args(args, expected):
    received: Queue = Queue()
    window = webview.create_window('Start func', html='<html><body></body></html>')
    start_args = {'func': lambda *params: received.put(params)}
    if args is not None:
        start_args['args'] = args
    run_test(webview, window, start_args=start_args)
    assert received.get(timeout=5) == expected


def test_start_returns_when_initialized_cancels_the_window():
    window = webview.create_window('Cancelled', html='<html><body></body></html>')
    renderers: Queue = Queue()

    def initialized(renderer):
        renderers.put(renderer)
        return False

    window.events.initialized += initialized
    webview.start()

    assert renderers.get(timeout=1) == webview.renderer
    assert window.native is None
    assert not window.events.shown.is_set()
