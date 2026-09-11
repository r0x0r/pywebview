"""
Deadlock regression tests.

These tests exercise a family of GUI-thread reentrancy deadlocks that were
shared across the backends.

Root cause
----------
A number of pywebview events are dispatched *synchronously* on the GUI thread so
that a handler can veto or mutate the outcome. These are the events created with
``should_lock=True`` in ``webview/window.py``::

    closing, before_show, before_load, initialized

When such a handler runs, it *is* the GUI thread. If it then called a synchronous
webview API (``evaluate_js``, ``run_js``, ``window.width``, ``get_current_url``,
``get_cookies``, a ``window.state`` update, a dialog, ...), the platform layer
posted the real work back to the GUI thread and blocked on a semaphore waiting
for the result::

    # e.g. cocoa.BrowserView.evaluate_js, before the fix
    AppHelper.callAfter(eval)            # queued onto the (blocked) GUI runloop
    JSResult.result_semaphore.acquire()  # GUI thread parks here forever

The queued work could never run, because the only thread that could run it was
parked. The same shape existed on GTK (``glib.idle_add`` + ``Semaphore.acquire``),
WinForms/EdgeChromium (``Invoke`` + async continuation + ``Semaphore.acquire``),
Qt and WinUI3.

The contract
------------
No pywebview API may block when called from the GUI thread. Two outcomes are
allowed, depending on what the API actually needs:

* the underlying native operation is **synchronous** (reading the window frame,
  reading the current URL, firing a fire-and-forget script) -- it runs inline on
  the calling thread and returns its value;
* the underlying native operation is **asynchronous** -- its result is delivered
  later, by the very thread that is asking, so it cannot be produced at all here.
  Those raise ``ReentrantCallError`` instead of blocking.

Which bucket an API falls into is backend-dependent (Qt caches cookies and can
answer ``get_cookies()`` inline; CEF answers from its own dedicated thread;
WebKit and WebView2 have to ask their cookie store asynchronously), so which of
the two outcomes is expected is pinned per renderer -- see
``RENDERERS_THAT_RAISE`` below -- rather than accepting either.

Reaching the fix: the lifecycle gate
-------------------------------------
The public ``Window`` methods above are also gated on readiness (e.g.
``window.width`` waits for the ``shown`` event, ``run_js()`` waits for
``before_load``) via ``webview.window._api_call()``. That gate had its own copy
of this bug: called reentrantly, from the very handler whose event it is
waiting for (or one that legitimately has not fired yet, like ``shown`` during
``before_show``), it would block for 20 seconds and then raise
``WebViewException`` -- without ever reaching the backend fix above.
``_api_call()`` now recognizes a call made from the thread currently
dispatching a ``should_lock`` event on this window and skips the wait,
so it falls through to the backend, which runs it inline or raises
``ReentrantCallError`` as described above. See
``webview.event.is_reentrant_dispatch()`` and ``Event.set()``.

This makes ``before_show`` and ``before_load`` handlers testable the same way
as ``closing`` (see ``LIFECYCLE_PHASES`` below). ``initialized`` is
deliberately excluded: it fires from ``Window._initialize()``, before
``guilib.create_window()`` has even run, so none of these APIs have a native
window to act on yet -- a lifecycle ordering issue, not a reentrancy one, and
out of scope here.

How a regression shows up
-------------------------
The call under test is made *directly* from the handler, on the GUI thread --
that is the only faithful reproduction. Dispatching it to a helper thread
instead would measure something else entirely: a background thread waiting on
a GUI thread that is merely *busy* running a handler is not a deadlock, it
just waits for the handler to return.

A blocking ``threading`` lock/semaphore acquire on the main thread cannot be
interrupted from another thread -- it does not poll for signals, so neither
``KeyboardInterrupt`` nor a watchdog calling ``interrupt_main()`` will break it.
A deadlocked call therefore parks the GUI thread for good, and ``webview.start()``
never returns either. To keep that bounded, the whole run is wrapped in a
``faulthandler`` watchdog: if ``start()`` has not returned within
``WATCHDOG_TIMEOUT`` the process is killed and every thread's stack is dumped,
which points straight at the blocked ``acquire()``. CI sees a hard failure with a
usable diagnosis instead of hanging until the job times out.
"""

import faulthandler
import os
import threading
import time

import pytest

import webview
from webview.errors import ReentrantCallError

# WinUI3 never fires `closing` for a programmatic `window.destroy()`: its handler
# is attached to AppWindow.Closing, which Microsoft.UI.Xaml.Window.Close() does
# not raise. Verified on CI -- the window loads, destroy() returns cleanly and
# start() finishes, with the handler never having run. That is a separate bug
# from the deadlocks under test here (it also means `closing` handlers and
# confirm_close are skipped on destroy()), and there is no public API to raise
# AppWindow.Closing by hand, so these cannot run there until it is fixed.
needs_closing_event = pytest.mark.skipif(
    os.environ.get('PYWEBVIEW_GUI') == 'winui3',
    reason='WinUI3 does not fire the closing event for a programmatic destroy()',
)

# How long to wait for the window to load before triggering the close.
LOAD_TIMEOUT = 10

# Upper bound on one window's whole lifecycle: load, close, and the call under
# test. Only ever reached if something is wedged -- a deadlocked call on the GUI
# thread, or a window that never opened and so can never be closed. Kept under
# the 60s pytest-timeout so this watchdog, which produces the stack dump, is what
# fires first.
WATCHDOG_TIMEOUT = 45


def _trigger_close(window):
    """Trigger the platform's native close path so the ``closing`` event fires.

    ``window.destroy()`` routes through the closing/FormClosing/closeEvent handler
    on GTK, WinForms, EdgeChromium and Qt. cocoa's ``destroy()`` calls
    ``NSWindow.close()`` which, unlike ``performClose_``, does *not* invoke
    ``windowShouldClose:`` and therefore never fires ``closing`` -- so for cocoa we
    call ``performClose_`` explicitly. WinUI3 has the same gap with no equivalent
    way around it; see ``needs_closing_event``.
    """
    native = window.native

    if native is not None and hasattr(native, 'performClose_'):
        from PyObjCTools import AppHelper

        AppHelper.callAfter(native.performClose_, None)
    else:
        window.destroy()


# The should_lock events for which the native window/webview already exist by
# the time the event fires, so a call from their handler is meaningful and not
# just "doesn't crash". `initialized` is deliberately excluded: it fires from
# `Window._initialize()`, before `guilib.create_window()` has run at all, so
# none of the actions below have a native window to act on yet regardless of
# the reentrancy fix -- that is a lifecycle ordering constraint, not something
# this suite covers.
LIFECYCLE_PHASES = ['before_show', 'before_load', 'closing']


def _call_from_lifecycle_handler(window, event_name, action):
    """Call ``action(window)`` on the GUI thread, from ``event_name``'s handler.

    Works for any of `LIFECYCLE_PHASES`. ``before_show``/``before_load`` fire on
    their own as the window starts up; ``closing`` only fires once something
    asks the window to close, which the closer thread below does via
    ``_trigger_close()``.

    Returns a state dict with ``value`` and ``error``. If the call deadlocks the
    watchdog kills the process, so a returned dict already proves it did not.
    """
    state = {'handler_ran': False, 'value': None, 'error': None}
    event = getattr(window.events, event_name)

    def on_event(*_args, **_kwargs):
        # This runs synchronously on the GUI thread (should_lock=True), so
        # `action` below is invoked *by the GUI thread itself*.
        state['handler_ran'] = True
        try:
            state['value'] = action(window)
        except BaseException as e:  # noqa: BLE001 - report anything the call hits
            state['error'] = e
        # Report from inside the handler rather than only through the assertions
        # below. On WinUI3 the process is torn down by Application.current.exit
        # when the last window closes, often before pytest prints its summary, so
        # this line is the only record of what happened that survives.
        print(f'[deadlock-test] value={state["value"]!r} error={state["error"]!r}', flush=True)
        # Returning (without vetoing) lets the window continue starting up (or
        # close), so start() returns.

    event += on_event

    def closer():
        # Close even if the page never finished loading. Skipping the close on a
        # load timeout would leave the window open, and webview.start() would
        # then never return -- turning a slow load into a hung run.
        state['loaded'] = window.events.loaded.wait(LOAD_TIMEOUT)
        time.sleep(0.5)
        try:
            _trigger_close(window)
            state['closed'] = True
        except BaseException as e:  # noqa: BLE001 - the watchdog is the real backstop
            state['close_error'] = e

    threading.Thread(target=closer, daemon=True).start()

    # A deadlocked call parks the GUI thread inside on_event, so start() never
    # returns either. Kill the process and dump every thread's stack rather than
    # hang; the dump names the blocked acquire().
    faulthandler.dump_traceback_later(WATCHDOG_TIMEOUT, exit=True)
    started = time.monotonic()
    try:
        webview.start()
    finally:
        faulthandler.cancel_dump_traceback_later()

    print(
        f'[deadlock-test] after start() in {time.monotonic() - started:.1f}s: {state}', flush=True
    )

    assert state['handler_ran'], (
        f'{event_name} event never fired, so nothing was tested '
        f'(loaded={state.get("loaded")}, close_error={state.get("close_error")!r})'
    )
    return state


# APIs whose native operation is synchronous on every backend: they must run
# inline on the GUI thread and hand back a value.
INLINE_ACTIONS = {
    'run_js': lambda w: w.run_js('1 + 1'),
    'width': lambda w: w.width,
    'height': lambda w: w.height,
    'x': lambda w: w.x,
    'y': lambda w: w.y,
    'get_current_url': lambda w: w.get_current_url(),
    'state_update': lambda w: setattr(w.state, 'deadlock_probe', 1),
}

# Validates the value `INLINE_ACTIONS[action_name]` produced (and, for
# `state_update`, the window state it was supposed to mutate), so that a
# backend returning a placeholder like `None` instead of the real result is
# caught, not just one that hangs or raises. Takes `(window, value)` because
# `state_update`'s own return value (from `setattr`) is always `None` -- what
# it actually needs to check is on `window.state`. `run_js()`'s result is
# deliberately not checked: per its own docstring "result of the code is not
# guaranteed to be returned and depends on the platform", so asserting a
# specific value here would itself be testing an unsupported contract; not
# raising is the only thing `run_js()` promises.
INLINE_ACTIONS_EXPECTATIONS = {
    'run_js': lambda w, v: True,
    'width': lambda w, v: isinstance(v, (int, float)) and v > 0,
    'height': lambda w, v: isinstance(v, (int, float)) and v > 0,
    'x': lambda w, v: isinstance(v, (int, float)),
    'y': lambda w, v: isinstance(v, (int, float)),
    'get_current_url': lambda w, v: v is None or (isinstance(v, str) and len(v) > 0),
    'state_update': lambda w, v: w.state.deadlock_probe == 1,
}

# APIs whose native operation may be asynchronous. Those backends cannot answer
# on the GUI thread at all and must say so instead of blocking.
ASYNC_CAPABLE_ACTIONS = {
    'evaluate_js': lambda w: w.evaluate_js('1 + 1'),
    'get_cookies': lambda w: w.get_cookies(),
}

# Renderers (``window.gui.renderer``) that must raise ``ReentrantCallError`` for
# a given action, because their result is delivered asynchronously by the GUI
# thread itself. Every other renderer answers the call inline instead: Qt caches
# cookies and calling either ``evaluate_js`` or ``get_cookies`` is synchronous;
# CEF answers ``evaluate_js``/``get_cookies`` from its own dedicated CEF thread;
# MSHTML runs ``evaluate_js`` synchronously and its ``get_cookies`` takes the
# WinForms "unsupported" path, returning ``[]`` without ever touching the GUI
# thread.
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


def _phase_params(actions):
    """Build (phase, action_name) parametrize entries, skipping `closing` on WinUI3."""
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
    """A synchronous API called from a blocking handler runs inline and returns.

    Covers ``before_show``, ``before_load`` and ``closing`` -- the blocking
    events that fire after the native window/webview already exist. (see
    ``LIFECYCLE_PHASES`` for why ``initialized`` is not included here.)
    """
    state = _call_from_lifecycle_handler(window, phase, INLINE_ACTIONS[action_name])

    assert state['error'] is None, (
        f'{action_name} is backed by a synchronous native call, so it must run '
        f'inline on the GUI thread rather than fail: {state["error"]!r}'
    )
    assert INLINE_ACTIONS_EXPECTATIONS[action_name](window, state['value']), (
        f'{action_name} ran inline but returned an unexpected value: {state["value"]!r}'
    )


@pytest.mark.parametrize('phase,action_name', _phase_params(ASYNC_CAPABLE_ACTIONS))
def test_async_capable_api_in_blocking_handler(window, phase, action_name):
    """An asynchronous API called from a blocking handler reports, never blocks.

    Whether it reports by raising ``ReentrantCallError`` or by returning a value
    is pinned per renderer via ``RENDERERS_THAT_RAISE``, not left to "either is
    fine" -- see that dict for which backends fall into which bucket and why.
    """
    state = _call_from_lifecycle_handler(window, phase, ASYNC_CAPABLE_ACTIONS[action_name])

    renderer = window.gui.renderer
    error = state['error']
    expects_raise = renderer in RENDERERS_THAT_RAISE.get(action_name, set())

    if expects_raise:
        assert isinstance(error, ReentrantCallError), (
            f'{action_name} on {renderer} must refuse a GUI-thread call with '
            f'ReentrantCallError, not {error!r}'
        )
    else:
        assert error is None, (
            f'{action_name} on {renderer} is answered inline (cached/synchronous), '
            f'so it must not raise: {error!r}'
        )


def test_reentrant_call_error_is_a_runtime_error():
    """``ReentrantCallError`` stays catchable as the ``RuntimeError`` it replaced."""
    assert issubclass(ReentrantCallError, RuntimeError)
