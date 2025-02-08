import pytest
import webview
from threading import Lock

from .util import run_test, wait_release



@pytest.fixture
def window():
    return webview.create_window('Evaluate JS test', html='<html><body><div id="node">TEST</div></body></html>')


def test_state(window):
    run_test(webview, window, state_test)


def test_state_before_start(window):
    window.state.test = 420
    run_test(webview, window, before_start_test)


def test_state_from_js(window):
    run_test(webview, window, state_from_js_test)


def test_state_dict(window):
    run_test(webview, window, state_dict_test)


def test_state_none(window):
    run_test(webview, window, state_none_test)


def test_persistence(window):
    run_test(webview, window, persistence_test)


def test_delete(window):
    run_test(webview, window, delete_test)


def test_delete_from_js(window):
    run_test(webview, window, delete_from_js_test)


def test_event_change(window):
    run_test(webview, window, event_change_test)


def test_event_delete(window):
    run_test(webview, window, event_delete_test)


def test_event_change_from_js(window):
    run_test(webview, window, event_change_from_js_test)


def test_event_delete_from_js(window):
    run_test(webview, window, event_delete_from_js_test)


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


def persistence_test(window):
    window.state.test = 420
    assert window.evaluate_js('pywebview.state.test === 420')

    window.load_html('<html><body>Reloaded</body></html>')
    assert window.evaluate_js('pywebview.state.test === 420')

    window.load_url("https://www.example.com")
    assert window.evaluate_js('pywebview.state.test === 420')


def delete_test(window):
    window.state.test = 420
    assert window.evaluate_js('pywebview.state.test === 420')
    del window.state.test
    assert window.evaluate_js('Object.keys(pywebview.state).length === 0')


def delete_from_js_test(window):
    window.state.test = 420
    assert window.evaluate_js('pywebview.state.test === 420')
    window.run_js('delete pywebview.state.test')
    assert 'test' not in window.state


def event_change_test(window):
    def on_change(event, name, value):
        assert event == 'change'
        assert name == 'test'
        assert value == 420

        wait_release(lock)

    lock = Lock()
    window.state += on_change
    window.evaluate_js('pywebview.state.test = 420')
    assert lock.acquire(3)


def event_delete_test(window):
    def on_delete(event, name, value):
        assert event == 'delete'
        assert name == 'test'
        assert value is None

        wait_release(lock)

    lock = Lock()
    window.state += on_delete
    window.evaluate_js('delete pywebview.state.test')
    assert lock.acquire(3)


def event_change_from_js_test(window):
    window.run_js('pywebview.state.addEventListener("change", event => { pywebview.state.result = `${event.detail.key}: ${event.detail.value}` })')
    window.state.test = 0
    assert window.state.result == 'test: 0'


def event_delete_from_js_test(window):
    window.run_js('pywebview.state.addEventListener("delete", event => { pywebview.state.result = event.detail.key })')
    window.state.test = 0
    assert window.evaluate_js('pywebview.state.test == 0')
    del window.state.test
    assert window.state.result == 'test'
