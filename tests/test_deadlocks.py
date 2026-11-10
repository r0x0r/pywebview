"""
Blocking handlers (before_show, before_load, closing) run on the GUI thread. Calling a synchronous
API from them used to deadlock, since the backend waited for a result that only the blocked GUI
thread could deliver. Each call here is made directly from the handler, so a regression hangs
until pytest-timeout fails the test.
"""

import asyncio
import os
import threading
import time

import pytest

import webview

ACTIONS = {
    'run_js': (lambda w: w.run_js('1 + 1'), lambda w, v: True),
    'width': (lambda w: w.width, lambda w, v: v > 0),
    'x': (lambda w: w.x, lambda w, v: isinstance(v, (int, float))),
    'get_current_url': (lambda w: w.get_current_url(), lambda w, v: v is None or v),
    'state': (lambda w: setattr(w.state, 'probe', 1), lambda w, v: w.state.probe == 1),
    'evaluate_js': (lambda w: w.evaluate_js('1 + 1'), lambda w, v: v == 2),
    'get_cookies': (lambda w: w.get_cookies(), lambda w, v: isinstance(v, list)),
}

# The result of these is produced by the page, which only exists once it starts loading.
NEEDS_PAGE = {'evaluate_js', 'get_cookies'}


def _params():
    for phase in ('before_show', 'before_load', 'closing'):
        for name in ACTIONS:
            if phase != 'closing' and name in NEEDS_PAGE:
                continue
            marks = []
            if phase == 'closing' and os.environ.get('PYWEBVIEW_GUI') == 'winui3':
                # WinUI3 does not fire closing for a programmatic destroy()
                marks.append(pytest.mark.skip(reason='closing does not fire on destroy()'))
            yield pytest.param(phase, name, marks=marks, id=f'{phase}-{name}')


def _close(window):
    native = window.native
    if hasattr(native, 'performClose_'):
        # Cocoa's destroy() skips windowShouldClose:, so closing would not fire
        from PyObjCTools import AppHelper

        AppHelper.callAfter(native.performClose_, None)
    else:
        window.destroy()


@pytest.mark.parametrize('use_async', [False, True], ids=['sync', 'async'])
@pytest.mark.parametrize('phase,name', list(_params()))
def test_api_in_blocking_handler(phase, name, use_async):
    window = webview.create_window('Deadlock test', html='<html><body>TEST</body></html>')
    action, check = ACTIONS[name]
    result = {}

    def handler():
        try:
            result['value'] = action(window)
        except Exception as e:
            result['error'] = e

    async def async_handler():
        handler()

    event = getattr(window.events, phase)
    event += async_handler if use_async else handler

    def closer():
        window.events.loaded.wait(10)
        _close(window)

    threading.Thread(target=closer, daemon=True).start()
    webview.start()

    assert result, f'{phase} handler never ran'
    assert 'error' not in result, result['error']
    assert check(window, result['value']), result['value']


@pytest.mark.parametrize('phase', ['before_show', 'before_load'])
@pytest.mark.parametrize('name', ['evaluate_js', 'get_cookies'])
def test_page_api_before_page_ready(phase, name):
    window = webview.create_window('Deadlock test', html='<html><body>TEST</body></html>')
    action = ACTIONS[name][0]
    result = {}

    def handler():
        try:
            action(window)
        except webview.errors.WebViewException as e:
            result['error'] = e

    event = getattr(window.events, phase)
    event += handler
    window.events.loaded += window.destroy
    webview.start()

    assert 'error' in result


def test_blocking_call_on_shared_loop_during_async_closing():
    """
    A coroutine on the shared loop blocks in a window method while an async closing handler is
    pending. The handler must not need the shared loop, or neither side can proceed.
    """
    result = {}

    class Api:
        async def quit(self):
            window.destroy()
            time.sleep(0.3)  # let the GUI thread enter the closing handler
            result['value'] = window.evaluate_js('1 + 1')

    async def closing():
        await asyncio.sleep(0)
        result['closing'] = True

    window = webview.create_window(
        'Deadlock test', html='<html><body>TEST</body></html>', js_api=Api()
    )
    window.events.closing += closing

    def func():
        window.events.loaded.wait(10)
        window.evaluate_js('pywebview.api.quit()')

    webview.start(func)

    assert result.get('closing'), result
