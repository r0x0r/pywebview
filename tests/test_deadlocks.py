"""
Deadlock regression tests.

These tests exercise a family of GUI-thread reentrancy deadlocks that are shared
across the backends.

Root cause
----------
A number of pywebview events are dispatched *synchronously* on the GUI thread so
that a handler can veto or mutate the outcome. These are the events created with
``should_lock=True`` in ``webview/window.py``::

    closing, before_show, before_load, initialized

When such a handler runs, it *is* the GUI thread. If it then calls a synchronous
webview API (``evaluate_js``, ``run_js``, ``window.width``, ``get_current_url``,
``get_cookies``, a ``window.state`` update, a file/confirmation dialog, ...), the
platform layer posts the real work back to the GUI thread and blocks on a
semaphore waiting for the result::

    # e.g. cocoa.BrowserView.evaluate_js
    AppHelper.callAfter(eval)          # queued onto the (blocked) GUI runloop
    JSResult.result_semaphore.acquire()  # GUI thread parks here forever

The queued work can never run because the GUI thread is parked on the semaphore,
so the call never returns. The same shape exists on GTK (``glib.idle_add`` +
``Semaphore.acquire``), WinForms/EdgeChromium (``Invoke`` + async continuation +
``Semaphore.acquire``), Qt and WinUI3.

Note: a blocking ``threading`` lock/semaphore acquire on the main thread cannot be
interrupted from another thread (it does not poll for signals), so once a real
deadlock is hit the process must be killed. To stay CI-safe these tests never let
the GUI thread park in the blocking call. Instead the ``closing`` handler runs the
synchronous API on a short-lived *probe* thread and waits for it with a timeout.
While the handler holds the GUI thread the probe cannot make progress, so a
timeout is a positive detection of the deadlock -- and the handler always returns,
so the window closes and ``webview.start()`` returns normally.

The tests assert the *desired* behaviour (the API returns), and are marked xfail
because the backends currently deadlock. Remove the xfail once a backend learns to
run these APIs inline when it is already on the GUI thread.
"""

import threading
import time

import pytest

import webview

# How long the probe waits for a synchronous API to return while the GUI thread
# is held by the closing handler. A healthy backend answers almost instantly.
PROBE_TIMEOUT = 4

# How long to wait for the window to load before triggering the close.
LOAD_TIMEOUT = 10


def _trigger_close(window):
    """Trigger the platform's native close path so the ``closing`` event fires.

    ``window.destroy()`` routes through the closing/FormClosing/closeEvent/AppWindow
    Closing handler on GTK, WinForms, EdgeChromium, Qt and WinUI3. cocoa's
    ``destroy()`` calls ``NSWindow.close()`` which, unlike ``performClose_``, does
    *not* invoke ``windowShouldClose:`` and therefore never fires ``closing`` -- so
    for cocoa we call ``performClose_`` explicitly.
    """
    native = window.native

    if native is not None and hasattr(native, 'performClose_'):
        from PyObjCTools import AppHelper

        AppHelper.callAfter(native.performClose_, None)
    else:
        window.destroy()


def _run_closing_deadlock_probe(window, action):
    """Run ``action(window)`` from inside a synchronous ``closing`` handler.

    Returns a state dict with ``deadlock`` (True if the call could not complete
    while the GUI thread was held), ``value`` and ``error``.
    """
    state = {'handler_ran': False, 'deadlock': None, 'value': None, 'error': None}

    def on_closing():
        # This runs synchronously on the GUI thread (closing is should_lock=True).
        state['handler_ran'] = True
        probe = {}

        def probe_call():
            try:
                probe['value'] = action(window)
            except BaseException as e:  # noqa: BLE001 - report anything the probe hits
                probe['error'] = e

        t = threading.Thread(target=probe_call, daemon=True)
        t.start()
        t.join(PROBE_TIMEOUT)

        state['deadlock'] = t.is_alive()
        state['value'] = probe.get('value')
        state['error'] = probe.get('error')
        # Returning (without vetoing) lets the window close so start() returns.

    window.events.closing += on_closing

    def closer():
        if not window.events.loaded.wait(LOAD_TIMEOUT):
            return
        time.sleep(0.5)
        _trigger_close(window)

    threading.Thread(target=closer, daemon=True).start()
    webview.start()

    return state


# Synchronous window APIs that dispatch to the GUI thread and block for a result.
# Each must be safe to call once the window is loaded/shown.
SYNC_ACTIONS = {
    'evaluate_js': lambda w: w.evaluate_js('1 + 1'),
    'run_js': lambda w: w.run_js('1 + 1'),
    'width': lambda w: w.width,
    'height': lambda w: w.height,
    'get_current_url': lambda w: w.get_current_url(),
    'get_cookies': lambda w: w.get_cookies(),
    'state_update': lambda w: w.state.__setattr__('deadlock_probe', 1),
}


@pytest.fixture
def window():
    return webview.create_window(
        'Deadlock test', html='<html><body><div id="node">TEST</div></body></html>'
    )


@pytest.mark.parametrize('action_name', list(SYNC_ACTIONS))
@pytest.mark.xfail(
    reason='Synchronous webview API called from a should_lock GUI-thread event '
    'handler (closing) deadlocks the GUI thread',
    strict=False,
)
def test_sync_api_in_closing_handler(window, action_name):
    """A synchronous webview API invoked from a ``closing`` handler must return."""
    state = _run_closing_deadlock_probe(window, SYNC_ACTIONS[action_name])

    assert state['handler_ran'], 'closing event never fired; cannot judge deadlock'
    assert not state['deadlock'], (
        f'{action_name}() deadlocked when called from a closing handler: the GUI '
        f'thread blocked waiting for work only it could run'
    )
