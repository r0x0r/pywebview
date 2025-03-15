import webview
import asyncio
import threading

from .util import assert_js, run_test


def test_expose_single():
    window = webview.create_window('JSBridge test', html='<html><body>TEST</body></html>')
    window.expose(get_int)
    run_test(webview, window, expose_single)


def test_expose_multiple():
    window = webview.create_window('JSBridge test', html='<html><body>TEST</body></html>')
    window.expose(get_int, get_float)
    run_test(webview, window, expose_multiple)


def test_expose_runtime():
    window = webview.create_window('JSBridge test', html='<html><body>TEST</body></html>')
    run_test(webview, window, expose_runtime)


def test_override():
    api = Api()
    window = webview.create_window('JSBridge test', html='<html><body>TEST</body></html>', js_api=api)
    window.expose(get_int)
    run_test(webview, window, expose_override)

def test_asyncio():
    loop = asyncio.new_event_loop()
    window = webview.create_window('JSBridge test', html='<html><body>TEST</body></html>', event_loop=loop)
    window.expose(get_async)

    threading.Thread(target=loop.run_forever).start()
    run_test(webview, window, expose_async)
    loop.call_soon_threadsafe(loop.stop)


async def get_async():
    await asyncio.sleep(1)
    return 7331

def get_int():
    return 420


def get_float():
    return 420.420


class Api:
    def get_int(self):
        return 421


def expose_single(window):
    assert_js(window, 'get_int', 420)


def expose_multiple(window):
    assert_js(window, 'get_int', 420)
    assert_js(window, 'get_float', 420.420)


def expose_runtime(window):
    window.expose(get_int, get_float)
    assert_js(window, 'get_int', 420)


def expose_override(window):
    assert_js(window, 'get_int', 420)

def expose_async(window):
    assert_js(window, 'get_async', 7331)
