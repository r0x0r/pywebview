import asyncio
import threading
from unittest.mock import MagicMock

import pytest

import webview
from webview import util
from webview.errors import WebViewException
from webview.event import Event, in_blocking_handler
from webview.menu import MenuAction
from webview.state import State
from webview.util import _TOKEN, js_bridge_call


@pytest.fixture(autouse=True)
def reset_event_loop():
    util.set_event_loop(None)
    yield
    util.stop_event_loop()


def test_async_js_api_function():
    returned = threading.Event()
    window = MagicMock()

    async def target(value):
        await asyncio.sleep(0.01)
        return value * 2

    window._functions = {'target': target}
    window.evaluate_js.side_effect = lambda script: returned.set()

    js_bridge_call(window, 'target', [21], 'value_id', _TOKEN)

    assert returned.wait(2)
    assert "{value: '42'}" in window.evaluate_js.call_args[0][0]


def test_async_event_handler_return_value():
    event = Event(MagicMock(), should_lock=True)
    calls = []

    async def handler():
        await asyncio.sleep(0.01)
        calls.append((threading.current_thread(), in_blocking_handler()))
        return False

    event += handler
    assert event.set() is True
    # Blocking handlers run on the thread that fired the event, not on the shared loop
    assert calls == [(threading.current_thread(), True)]


def test_start_rejects_its_own_running_loop():
    async def main():
        webview.create_window('Async test', html='<html></html>')
        with pytest.raises(WebViewException, match='event_loop'):
            webview.start(event_loop=asyncio.get_running_loop())

    asyncio.run(main())


def test_supplied_event_loop_is_used_and_left_open():
    loop = asyncio.new_event_loop()
    util.set_event_loop(loop)

    async def running_loop():
        return asyncio.get_running_loop()

    assert util.run_async(running_loop()) is loop

    util.stop_event_loop()
    assert not loop.is_closed()
    loop.call_soon_threadsafe(loop.stop)


def test_automatic_event_loop_is_closed_on_stop():
    async def running_loop():
        return asyncio.get_running_loop()

    loop = util.run_async(running_loop())
    util.stop_event_loop()
    assert loop.is_closed()


def test_async_evaluate_js_callback():
    called = threading.Event()
    window = MagicMock()

    async def callback(value):
        await asyncio.sleep(0.01)
        assert value == {'a': 1}
        called.set()

    window._callbacks = {'value_id': callback}
    js_bridge_call(window, 'pywebviewAsyncCallback', '{"a": 1}', 'value_id', _TOKEN)

    assert called.wait(2)


def test_async_state_handler():
    called = threading.Event()
    state = State(MagicMock())

    async def handler(event_type, key, value):
        await asyncio.sleep(0.01)
        assert (key, value) == ('foo', 'bar')
        called.set()

    state += handler
    state.foo = 'bar'

    assert called.wait(2)


def test_async_menu_action():
    async def action():
        await asyncio.sleep(0.01)
        return 'done'

    menu_action = MenuAction('Action', action)

    assert menu_action.function.__name__ == 'action'
    assert menu_action.function() == 'done'


def test_async_start_func():
    async def func(value):
        await asyncio.sleep(0.01)
        return value

    assert util.call_maybe_async(func, 42) == 42
