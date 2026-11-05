"""
Blocking handlers (before_show, before_load, closing) run on the GUI thread. Calling a synchronous
API from them used to deadlock, since the backend waited for a result that only the blocked GUI
thread could deliver. Each call here is made directly from the handler, so a regression hangs
until pytest-timeout fails the test.
"""

import os
import threading

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


@pytest.mark.parametrize('phase,name', list(_params()))
def test_api_in_blocking_handler(phase, name):
    window = webview.create_window('Deadlock test', html='<html><body>TEST</body></html>')
    action, check = ACTIONS[name]
    result = {}

    def handler():
        try:
            result['value'] = action(window)
        except Exception as e:
            result['error'] = e

    event = getattr(window.events, phase)
    event += handler

    def closer():
        window.events.loaded.wait(10)
        _close(window)

    threading.Thread(target=closer, daemon=True).start()
    webview.start()

    assert result, f'{phase} handler never ran'
    assert 'error' not in result, result['error']
    assert check(window, result['value']), result['value']
