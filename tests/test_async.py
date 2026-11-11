import asyncio
import threading
from unittest.mock import MagicMock

import pytest

import webview
from webview import util
from webview.errors import WebViewException
from webview.event import Event
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


def test_async_handler_on_non_blocking_event():
    called = threading.Event()
    event = Event(MagicMock())

    async def handler():
        await asyncio.sleep(0.01)
        called.set()

    event += handler
    event.set()

    assert called.wait(2)


def test_blocking_event_rejects_async_handler():
    event = Event(MagicMock(), should_lock=True, name='closing')

    async def handler():
        return False

    with pytest.raises(TypeError, match='window.events.closing is a blocking event'):
        event += handler

    assert len(event) == 0


def test_blocking_event_discards_returned_coroutine(caplog):
    event = Event(MagicMock(), should_lock=True, name='closing')

    async def handler():
        return False

    event += lambda: handler()

    # The coroutine is not awaited, so its False return value does not cancel closing
    assert event.set() is False
    assert 'cannot have async handlers' in caplog.text


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
