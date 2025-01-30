import pytest
import webview

from .util import run_test


@pytest.fixture
def window():
    return webview.create_window('Evaluate JS test', html='<html><body><div id="node">TEST</div></body></html>')


def test_state(window):
    run_test(webview, window, state_test)


def test_state_before_start(window):
    window.state = 420
    run_test(webview, window, before_start_test)


def test_state_from_js(window):
    run_test(webview, window, state_from_js_test)


def test_state_dict(window):
    run_test(webview, window, state_dict_test)


def test_state_none(window):
    run_test(webview, window, state_none_test)

def state_test(window):
    window.state.test = 420

    assert window.evaluate_js('pywebview.state.test === 420')


def before_start_test(window):
    assert window.evaluate_js('pywebview.state.test === 420')


def state_from_js_test(window):
     window.run_js('pywebview.state.test = 420')
     assert window.state.test == 420


def state_dict_test(window):
    window.state.test = { 'test1': 'test1', 'test2': 2 }
    assert window.evaluate_js('JSON.stringify(pywebview.state.test) === JSON.stringify({ "test1": "test1", "test2": 2}) ')


def state_none_test(window):
    window.state.test = None
    assert window.evaluate_js('pywebview.state.test === null')