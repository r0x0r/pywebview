import ctypes
import os
import time

import pytest

import webview

from .util import run_test

HTML = """
<body style="margin: 0; background: transparent">
    <div id="box" style="width: 200px; height: 200px; background: red"
         onclick="window.clicks = (window.clicks || 0) + 1"></div>
    <script>
        window.addEventListener('mouseup', () => window.releases = (window.releases || 0) + 1)
    </script>
</body>
"""

_WM_CANCELMODE = 0x001F
_WM_LBUTTONDOWN = 0x0201
_WM_LBUTTONUP = 0x0202
_MK_LBUTTON = 0x0001


@pytest.mark.skipif(
    os.environ.get('PYWEBVIEW_GUI') != 'win32',
    reason='mouse input is forwarded to the page by the win32 backend only',
)
def test_transparent_click():
    window = webview.create_window(
        'Transparent window', html=HTML, transparent=True, frameless=True
    )
    run_test(webview, window, click)


@pytest.mark.skipif(
    os.environ.get('PYWEBVIEW_GUI') != 'win32',
    reason='mouse input is forwarded to the page by the win32 backend only',
)
def test_transparent_capture_lost():
    window = webview.create_window(
        'Transparent window', html=HTML, transparent=True, frameless=True
    )
    run_test(webview, window, capture_lost)


def _post_message(hwnd: int, msg: int, wparam: int, lparam: int) -> None:
    # Looked up here, not at import: ctypes.WinDLL exists only on Windows, and
    # the module is collected on every platform.
    post_message = ctypes.WinDLL('user32').PostMessageW
    post_message.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t]
    post_message(hwnd, msg, wparam, lparam)


def click(window):
    # A transparent window has no WebView2 child window of its own: the
    # window procedure forwards the mouse to the page.
    window.events.loaded.wait()
    position = (50 << 16) | 50
    _post_message(window.native.hwnd, _WM_LBUTTONDOWN, _MK_LBUTTON, position)
    _post_message(window.native.hwnd, _WM_LBUTTONUP, 0, position)
    time.sleep(0.5)

    assert window.evaluate_js('window.clicks') == 1


def capture_lost(window):
    # A press whose capture is taken away, as by easy_drag's window drag,
    # is released for the page, without clicking what was pressed.
    window.events.loaded.wait()
    position = (50 << 16) | 50
    _post_message(window.native.hwnd, _WM_LBUTTONDOWN, _MK_LBUTTON, position)
    _post_message(window.native.hwnd, _WM_CANCELMODE, 0, 0)
    time.sleep(0.5)

    assert window.evaluate_js('[window.releases, window.clicks]') == [1, None]
