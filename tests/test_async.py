import asyncio
import threading
from unittest.mock import MagicMock

import pytest

from webview import util
from webview.event import Event
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

    async def handler():
        await asyncio.sleep(0.01)
        return False

    event += handler
    assert event.set() is True


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
