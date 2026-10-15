"""
Calling pywebview from a blocking (should_lock) event handler, which runs on the GUI thread,
must never block: synchronous APIs run inline, asynchronous ones raise ReentrantCallError.

A deadlock parks the GUI thread uninterruptibly, so each run is wrapped in a faulthandler
watchdog that kills the process and dumps the stacks instead of hanging.
"""

import faulthandler
import os
import threading
import time

import pytest

import webview
from webview.errors import ReentrantCallError

# WinUI3 does not fire closing for a programmatic destroy()
needs_closing_event = pytest.mark.skipif(
    os.environ.get('PYWEBVIEW_GUI') == 'winui3',
    reason='WinUI3 does not fire the closing event for a programmatic destroy()',
)

LOAD_TIMEOUT = 10
# Kept under the 60s pytest-timeout, so the watchdog fires first and dumps the stacks
WATCHDOG_TIMEOUT = 45

# initialized is excluded, as it fires before the native window exists
LIFECYCLE_PHASES = ['before_show', 'before_load', 'closing']

# APIs that must run inline, paired with a validator for the value they return
INLINE_ACTIONS = {
    'run_js': (lambda w: w.run_js('1 + 1'), lambda w, v: True),
    'width': (lambda w: w.width, lambda w, v: isinstance(v, (int, float)) and v > 0),
    'height': (lambda w: w.height, lambda w, v: isinstance(v, (int, float)) and v > 0),
    'x': (lambda w: w.x, lambda w, v: isinstance(v, (int, float))),
    'y': (lambda w: w.y, lambda w, v: isinstance(v, (int, float))),
    'get_current_url': (
        lambda w: w.get_current_url(),
        lambda w, v: v is None or (isinstance(v, str) and len(v) > 0),
    ),
    'state_update': (
        lambda w: setattr(w.state, 'deadlock_probe', 1),
        lambda w, v: w.state.deadlock_probe == 1,
    ),
}

# APIs that are asynchronous on some backends, paired with a validator for inline results
ASYNC_CAPABLE_ACTIONS = {
    'evaluate_js': (lambda w: w.evaluate_js('1 + 1'), lambda v: v == 2),
    'get_cookies': (lambda w: w.get_cookies(), lambda v: isinstance(v, list)),
}

# Renderers that must raise ReentrantCallError. Others answer inline.
RENDERERS_THAT_RAISE = {
    'evaluate_js': {
        'wkwebview',
        'gtkwebkit2',
        'edgechromium',
        'winui3',
        'android-webkit',
        'qtwebengine',
    },
    'get_cookies': {'wkwebview', 'gtkwebkit2', 'edgechromium', 'winui3', 'android-webkit'},
}


@pytest.fixture
def window():
    return webview.create_window(
        'Deadlock test', html='<html><body><div id="node">TEST</div></body></html>'
    )


def _trigger_close(window):
    # Cocoa's destroy() does not fire closing, while performClose_ does
    native = window.native

    if native is not None and hasattr(native, 'performClose_'):
        from PyObjCTools import AppHelper

        AppHelper.callAfter(native.performClose_, None)
    else:
        window.destroy()


def _call_from_lifecycle_handler(window, event_name, action):
    state = {'handler_ran': False, 'value': None, 'error': None}

    def on_event():
        state['handler_ran'] = True
        try:
            state['value'] = action(window)
        except BaseException as e:
            state['error'] = e

    def closer():
        # Close even if the page never loaded, so that start() returns
        state['loaded'] = window.events.loaded.wait(LOAD_TIMEOUT)
        time.sleep(0.5)
        try:
            _trigger_close(window)
        except BaseException as e:
            state['close_error'] = e

    event = getattr(window.events, event_name)
    event += on_event
    threading.Thread(target=closer, daemon=True).start()

    faulthandler.dump_traceback_later(WATCHDOG_TIMEOUT, exit=True)
    try:
        webview.start()
    finally:
        faulthandler.cancel_dump_traceback_later()

    assert state['handler_ran'], f'{event_name} never fired: {state}'
    return state


def _phase_params(actions):
    return [
        pytest.param(
            phase,
            action_name,
            marks=[needs_closing_event] if phase == 'closing' else [],
            id=f'{phase}-{action_name}',
        )
        for phase in LIFECYCLE_PHASES
        for action_name in actions
    ]


@pytest.mark.parametrize('phase,action_name', _phase_params(INLINE_ACTIONS))
def test_inline_api_in_blocking_handler(window, phase, action_name):
    action, is_valid = INLINE_ACTIONS[action_name]
    state = _call_from_lifecycle_handler(window, phase, action)

    assert state['error'] is None, f'{action_name} must run inline: {state["error"]!r}'
    assert is_valid(window, state['value']), f'{action_name} returned {state["value"]!r}'


@pytest.mark.parametrize('phase,action_name', _phase_params(ASYNC_CAPABLE_ACTIONS))
def test_async_capable_api_in_blocking_handler(window, phase, action_name):
    action, is_valid = ASYNC_CAPABLE_ACTIONS[action_name]
    state = _call_from_lifecycle_handler(window, phase, action)
    renderer = window.gui.renderer

    if renderer in RENDERERS_THAT_RAISE[action_name]:
        assert isinstance(state['error'], ReentrantCallError), (
            f'{action_name} on {renderer} must raise ReentrantCallError: {state["error"]!r}'
        )
    else:
        assert state['error'] is None, f'{action_name} on {renderer}: {state["error"]!r}'
        assert is_valid(state['value']), f'{action_name} returned {state["value"]!r}'


def test_reentrant_call_error_is_a_runtime_error():
    assert issubclass(ReentrantCallError, RuntimeError)
