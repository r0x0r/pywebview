"""Frame styles for frameless windows (``KEEP_FRAME_STYLES``).

The Windows helpers only exist on Windows, so these tests are skipped elsewhere. Everything they
assert is pure flag arithmetic - the behaviour itself (``Win``+arrows, maximize covering the work
area) is verified by hand with real keyboard input, since CI has no display.
"""

from __future__ import annotations

import sys

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != 'win32', reason='webview.platforms.win32 is Windows only'
)


def test_frame_styles_is_the_set_frameless_windows_lack():
    from webview.platforms.win32 import FRAME_STYLES

    # WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU
    assert FRAME_STYLES == 0x00040000 | 0x00020000 | 0x00010000 | 0x00080000
    assert FRAME_STYLES == 0x000F0000


def test_with_frame_styles_adds_them():
    from webview.platforms.win32 import FRAME_STYLES, with_frame_styles

    assert with_frame_styles(0) == FRAME_STYLES
    assert with_frame_styles(0x10000000) == 0x10000000 | FRAME_STYLES  # WS_VISIBLE kept


def test_with_frame_styles_is_idempotent():
    from webview.platforms.win32 import FRAME_STYLES, with_frame_styles

    assert with_frame_styles(FRAME_STYLES) == FRAME_STYLES
    assert with_frame_styles(with_frame_styles(0x00C00000)) == 0x00C00000 | FRAME_STYLES


def test_frame_styles_installs_and_uninstalls():
    """A real window: subclassing it and restoring it must both work."""
    import ctypes

    from webview.platforms.win32 import FrameStyles

    user32 = ctypes.WinDLL('user32', use_last_error=True)
    user32.CreateWindowExW.restype = ctypes.c_void_p
    hwnd = user32.CreateWindowExW(
        0, 'STATIC', 'frame-styles-test', 0x80000000, 0, 0, 100, 100, None, None, None, None
    )
    assert hwnd, 'could not create a test window'

    try:
        styles = FrameStyles(hwnd)
        assert styles.install() is True
        assert styles.installed is True
        assert styles._old_style is not None
        # WS_THICKFRAME must be there now, and the client rect must still equal the window rect
        assert user32.GetWindowLongW(ctypes.c_void_p(hwnd), -16) & 0x00040000

        rect, client = (ctypes.c_long * 4)(), (ctypes.c_long * 4)()
        user32.GetWindowRect(ctypes.c_void_p(hwnd), ctypes.byref(rect))
        user32.GetClientRect(ctypes.c_void_p(hwnd), ctypes.byref(client))
        assert (rect[2] - rect[0], rect[3] - rect[1]) == (
            client[2] - client[0],
            client[3] - client[1],
        )

        styles.uninstall()
        assert styles.installed is False
    finally:
        user32.DestroyWindow(ctypes.c_void_p(hwnd))
