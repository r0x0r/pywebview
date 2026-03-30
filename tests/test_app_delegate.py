"""
Test that NSApp.delegate is cleared when the owning window closes.

NSApp.delegate uses assign semantics per Apple's documentation —
delegating objects do not retain their delegates. The caller is
responsible for ensuring the delegate remains alive. In multi-window
scenarios, if the window whose appDelegate is the current NSApp.delegate
closes while other windows remain open, pywebview must clear
NSApp.delegate to avoid leaving a pointer to a delegate that may be
freed.
"""

import sys
import time

import pytest

pytestmark = pytest.mark.skipif(sys.platform != 'darwin', reason='NSApp.delegate is macOS only')


def test_app_delegate_cleared_when_owning_window_closes():
    """When a child window whose appDelegate is NSApp.delegate closes
    while the parent is still open, NSApp.delegate must be cleared.

    Without this, NSApp.delegate points to a delegate whose owning
    BrowserView has been destroyed. Per Apple's docs, delegate properties
    use assign semantics — the delegating object does not retain the
    delegate, so the caller must ensure it stays alive. Clearing the
    pointer on close upholds this contract.
    """
    import objc

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

        delegate_before = BrowserView.app.delegate()
        result['before_addr'] = objc.pyobjc_id(delegate_before) if delegate_before else 0
        del delegate_before

        child.destroy()
        time.sleep(0.5)

        delegate_after = BrowserView.app.delegate()
        after_addr = objc.pyobjc_id(delegate_after) if delegate_after else 0
        result['after_addr'] = after_addr
        result['still_points_to_child'] = after_addr == result['before_addr'] and after_addr != 0
        del delegate_after

        parent.destroy()

    parent = webview.create_window(
        'Parent',
        html='<html><body>parent</body></html>',
    )
    webview.start(check_delegate, parent, debug=False)

    assert not result.get('still_points_to_child', False), (
        f"NSApp.delegate still points to closed child window's delegate "
        f'(addr {result.get("before_addr", "?"):#x}). '
        f'Per Apple docs, delegate properties use assign semantics — '
        f'the delegating object does not retain the delegate. '
        f'Leaving this pointer after the owning BrowserView is destroyed '
        f'risks a use-after-free crash.'
    )
