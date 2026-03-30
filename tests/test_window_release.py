"""
Test that BrowserView sets releasedWhenClosed to False.

NSWindow defaults to releasedWhenClosed=YES, which means Cocoa silently
releases the window when it closes.  BrowserView.__init__ also calls
.retain() on the window and windowWillClose_ calls .release() — a
balanced pair.  But with releasedWhenClosed=YES, Cocoa adds an untracked
third release on close, eventually over-releasing the window to rc=0.

The freed memory is later accessed by a stale Cocoa callback (e.g. from
WebKit's async IPC), triggering a pointer authentication trap (SIGTRAP)
on ARM64 — a hard crash, not a catchable exception.

Confirmed via lldb: setting a breakpoint on [NSWindow dealloc] shows the
window being deallocated (dealloc called twice on the same address due
to the over-release), followed by a crash when object_getClass accesses
the freed address.

The fix: setReleasedWhenClosed_(False) after window creation.
"""

import inspect
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

pytestmark = pytest.mark.skipif(sys.platform != 'darwin', reason='NSWindow is macOS only')


def test_pywebview_disables_released_when_closed():
    """BrowserView.__init__ must call setReleasedWhenClosed_(False)."""
    from webview.platforms.cocoa import BrowserView

    source = inspect.getsource(BrowserView.__init__)
    assert 'setReleasedWhenClosed_(False)' in source


@pytest.mark.skipif(not shutil.which('lldb'), reason='lldb not available')
def test_no_double_dealloc_on_window_close():
    """Verify [NSWindow dealloc] is not called on a window that was already
    deallocated.  Without setReleasedWhenClosed_(False), the window is
    over-released: Cocoa's releasedWhenClosed auto-release plus pywebview's
    manual .release() in windowWillClose_ cause a double dealloc, which
    leads to a SIGTRAP when a stale callback accesses the freed memory.

    This test runs the multi-window test sequence under lldb with a
    breakpoint on [NSWindow dealloc] and verifies:
      1. No crash (exit code 0)
      2. No address appears in more than one dealloc
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        logfile = f.name

    try:
        result = subprocess.run(
            [
                'lldb',
                '--batch',
                '-o',
                'breakpoint set -n "-[NSWindow initWithContentRect:styleMask:backing:defer:]" '
                "-C \"script print('ALLOC:'+hex(lldb.frame.FindRegister('x0').GetValueAsUnsigned()))\" "
                '-G true',
                '-o',
                'breakpoint set -n "-[NSWindow dealloc]" '
                "-C \"script print('DEALLOC:'+hex(lldb.frame.FindRegister('x0').GetValueAsUnsigned()))\" "
                '-G true',
                '-o',
                'process launch -- -m pytest --no-header -q '
                'tests/test_multi_window.py::test_bg_color '
                'tests/test_multi_window.py::test_load_html '
                'tests/test_multi_window.py::test_load_url',
                '-k',
                'script print("CRASH:"+hex(lldb.frame.FindRegister("x0").GetValueAsUnsigned()))',
                '-k',
                'quit',
                '--',
                sys.executable,
            ],
            capture_output=True,
            timeout=180,
            text=True,
        )

        output = result.stdout + result.stderr

        # Collect alloc, dealloc, and crash events in order
        events = []
        crash_addr = None
        for line in output.splitlines():
            if line.startswith('ALLOC:'):
                events.append(('alloc', line.split(':')[1]))
            elif line.startswith('DEALLOC:'):
                events.append(('dealloc', line.split(':')[1]))
            elif line.startswith('CRASH:'):
                crash_addr = line.split(':')[1]

        # With the fix: no crash
        assert (
            crash_addr is None
        ), f'Window at {crash_addr} was accessed after dealloc.\nEvents: {events}'
        assert result.returncode == 0, (
            f'Process exited with {result.returncode}.\n'
            f'Events: {events}\n'
            f'Output (last 500 chars): {output[-500:]}'
        )

        # Check no address is deallocated without a preceding alloc.
        # An address that is deallocated, then allocated again, then
        # deallocated again is fine (address reuse).  But dealloc
        # without a matching alloc, or two deallocs in a row, indicates
        # an over-release.
        live = set()  # addresses that have been allocated but not yet deallocated
        for event, addr in events:
            if event == 'alloc':
                live.add(addr)
            elif event == 'dealloc':
                assert addr in live, (
                    f'Window {addr} deallocated without a preceding alloc '
                    f'(double dealloc / over-release).\n'
                    f'Events: {events}'
                )
                live.discard(addr)

    finally:
        os.unlink(logfile)
