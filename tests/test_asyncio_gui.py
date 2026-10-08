import asyncio

import webview

from .test_asyncio import event_loop as event_loop
from .util import assert_js, run_test


class Api:
    async def answer(self, value):
        await asyncio.sleep(0.01)
        return value

    async def fail(self):
        await asyncio.sleep(0)
        raise ValueError('async failure')


def test_async_js_api(event_loop):
    window = webview.create_window('Async JS API', html='<html></html>', js_api=Api())

    def check(window):
        assert_js(window, 'answer', 42, 42)
        assert_js(window, 'fail', 'error')

    run_test(webview, window, check, start_args={'event_loop': event_loop})


def test_async_expose(event_loop):
    async def answer():
        await asyncio.sleep(0.01)
        return 42

    window = webview.create_window('Async expose', html='<html></html>')
    window.expose(answer)
    run_test(
        webview,
        window,
        lambda window: assert_js(window, 'answer', 42),
        start_args={'event_loop': event_loop},
    )
