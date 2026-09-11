"""
The `closing` event must fire for a programmatic `window.destroy()`, not only
for a close the user starts from the title bar.

`closing` is what lets an application veto a close or clean up before one, and
`confirm_close` is built on the same path, so a backend that fires it only for
user-initiated closes silently drops both whenever the app closes its own
window.

GTK (`delete-event`), Qt (`closeEvent`) and WinForms (`FormClosing`) all route
`destroy()` through the same native path the title-bar button uses, so they get
this for free. WinUI3 does not: its handler is attached to `AppWindow.Closing`,
which `Microsoft.UI.Xaml.Window.Close()` never raises, so `BrowserForm.close()`
runs the flow itself.

cocoa has the same gap -- `destroy()` calls `NSWindow.close()`, which, unlike
`performClose_`, does not invoke `windowShouldClose:` -- and is skipped below
rather than fixed here.
"""

import faulthandler
import sys
import threading
import time

import pytest

import webview

# Bound on one window's whole lifecycle. Only reached if a window will not close
# -- e.g. a veto that is never lifted -- in which case start() would otherwise
# block forever. Killing the process dumps every thread's stack, which says far
# more than a hung job does.
WATCHDOG_TIMEOUT = 45

LOAD_TIMEOUT = 10

pytestmark = pytest.mark.skipif(
    sys.platform == 'darwin',
    reason="cocoa's destroy() uses NSWindow.close(), which never fires closing",
)


def _run(window, closer):
    """Start ``window``, driving it from ``closer`` on a background thread."""
    threading.Thread(target=closer, daemon=True).start()

    faulthandler.dump_traceback_later(WATCHDOG_TIMEOUT, exit=True)
    try:
        webview.start()
    finally:
        faulthandler.cancel_dump_traceback_later()


def _make_window(title):
    return webview.create_window(title, html='<html><body>closing</body></html>')


def test_closing_fires_on_destroy():
    """``window.destroy()`` fires ``closing``, like a title-bar close would."""
    window = _make_window('closing on destroy')
    fired = threading.Event()

    window.events.closing += fired.set

    def closer():
        window.events.loaded.wait(LOAD_TIMEOUT)
        time.sleep(0.5)
        window.destroy()

    _run(window, closer)

    assert fired.is_set(), 'closing did not fire for window.destroy()'


def test_closing_handler_can_veto_destroy():
    """A ``closing`` handler returning False cancels a programmatic destroy."""
    window = _make_window('closing veto')
    attempts = []
    vetoed = threading.Event()

    def on_closing():
        attempts.append(len(attempts) + 1)
        if len(attempts) == 1:
            vetoed.set()
            return False  # veto this one; the window must stay open
        return None  # let the second attempt through, so start() returns

    window.events.closing += on_closing

    def closer():
        window.events.loaded.wait(LOAD_TIMEOUT)
        time.sleep(0.5)
        window.destroy()

        # If the veto was honoured the window is still up, so this second
        # destroy is what actually closes it. If it was not, the window is
        # already gone and this is a no-op -- the assertions below catch that.
        vetoed.wait(LOAD_TIMEOUT)
        time.sleep(0.5)
        window.destroy()

    _run(window, closer)

    assert len(attempts) == 2, (
        f'expected the vetoed destroy to leave the window open and a second '
        f'destroy to close it, got {len(attempts)} closing event(s)'
    )
