"""
Test that the app delegate is shared and properly managed.

BrowserView uses a single shared AppDelegate for the NSApplication
singleton, rather than creating one per window. The delegate is set when
the first window is created and cleared when the last window closes.
"""

import sys
import time

import pytest

pytestmark = pytest.mark.skipif(sys.platform != 'darwin', reason='NSApp.delegate is macOS only')


def test_app_delegate_survives_child_close():
    """NSApp.delegate must remain set while any window is still open.

    With a shared delegate, closing a child window should not clear
    NSApp.delegate — the parent window still needs it.
    """

    import webview
    from webview.platforms.cocoa import BrowserView

    result = {}

    def check_delegate(parent):
        parent.events.loaded.wait(timeout=10)

        child = webview.create_window(
            'Child',
            html='<html><body>child</body></html>',
        )
        child.events.loaded.wait(timeout=10)

        result['before'] = BrowserView.app.delegate() is not None

        child.destroy()
        time.sleep(0.5)

        result['after_child_close'] = BrowserView.app.delegate() is not None

        parent.destroy()

    parent = webview.create_window(
        'Parent',
        html='<html><body>parent</body></html>',
    )
    webview.start(check_delegate, parent, debug=False)

    assert result.get('before'), 'NSApp.delegate should be set while windows are open'
    assert result.get(
        'after_child_close'
    ), 'NSApp.delegate should still be set after child closes — parent is still open'


def test_app_delegate_cleared_when_last_window_closes():
    """NSApp.delegate must be cleared when the last window closes."""
    import webview
    from webview.platforms.cocoa import BrowserView

    result = {}

    def check_delegate(window):
        window.events.loaded.wait(timeout=10)
        result['before'] = BrowserView.app.delegate() is not None
        window.destroy()
        time.sleep(0.5)
        result['after'] = BrowserView._shared_app_delegate

    window = webview.create_window(
        'Test',
        html='<html><body>test</body></html>',
    )
    webview.start(check_delegate, window, debug=False)

    assert result.get('before'), 'NSApp.delegate should be set while window is open'
    assert (
        result.get('after') is None
    ), 'Shared app delegate should be None after last window closes'
