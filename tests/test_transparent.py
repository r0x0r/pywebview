import ctypes
import os
import time
from ctypes import wintypes

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

TOUCH_HTML = """
<body style="margin: 0; background: transparent">
    <div style="width: 200px; height: 200px; background: red"
         onpointerdown="window.touch = [event.pointerType, event.clientX, event.clientY]"></div>
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


@pytest.mark.skipif(
    os.environ.get('PYWEBVIEW_GUI') != 'win32',
    reason='touch input is forwarded to the page by the win32 backend only',
)
def test_transparent_touch():
    # On top: the touch goes to whatever window is at its point, and the
    # test's window may not be brought to the foreground.
    window = webview.create_window(
        'Transparent window', html=TOUCH_HTML, transparent=True, frameless=True, on_top=True
    )
    run_test(webview, window, touch)


class _POINTER_INFO(ctypes.Structure):
    _fields_ = [
        ('pointerType', ctypes.c_uint32),
        ('pointerId', ctypes.c_uint32),
        ('frameId', ctypes.c_uint32),
        ('pointerFlags', ctypes.c_uint32),
        ('sourceDevice', wintypes.HANDLE),
        ('hwndTarget', wintypes.HWND),
        ('ptPixelLocation', wintypes.POINT),
        ('ptHimetricLocation', wintypes.POINT),
        ('ptPixelLocationRaw', wintypes.POINT),
        ('ptHimetricLocationRaw', wintypes.POINT),
        ('dwTime', wintypes.DWORD),
        ('historyCount', ctypes.c_uint32),
        ('InputData', ctypes.c_int32),
        ('dwKeyStates', wintypes.DWORD),
        ('PerformanceCount', ctypes.c_uint64),
        ('ButtonChangeType', ctypes.c_int),
    ]


class _POINTER_TOUCH_INFO(ctypes.Structure):
    _fields_ = [
        ('pointerInfo', _POINTER_INFO),
        ('touchFlags', ctypes.c_uint32),
        ('touchMask', ctypes.c_uint32),
        ('rcContact', wintypes.RECT),
        ('rcContactRaw', wintypes.RECT),
        ('orientation', ctypes.c_uint32),
        ('pressure', ctypes.c_uint32),
    ]


class _POINTER_TYPE_INFO(ctypes.Structure):
    _fields_ = [('type', ctypes.c_uint32), ('touchInfo', _POINTER_TOUCH_INFO)]


def touch(window):
    # A touch is real input, which goes to whatever window is at its point:
    # it is injected through a synthetic touch device, at the window's
    # client point (50, 50) in physical pixels.
    window.events.loaded.wait()
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    user32.CreateSyntheticPointerDevice.restype = wintypes.HANDLE
    user32.InjectSyntheticPointerInput.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(_POINTER_TYPE_INFO),
        ctypes.c_uint32,
    ]
    user32.DestroySyntheticPointerDevice.argtypes = [wintypes.HANDLE]
    device = user32.CreateSyntheticPointerDevice(2, 1, 1)  # PT_TOUCH, 1 contact
    if not device:
        pytest.skip(f'no synthetic touch device: {ctypes.WinError(ctypes.get_last_error())}')

    hwnd = window.native.hwnd
    user32.SetForegroundWindow(hwnd)
    point = wintypes.POINT(50, 50)
    user32.ClientToScreen(hwnd, ctypes.byref(point))
    try:
        # POINTER_FLAG_DOWN | _INRANGE | _INCONTACT, then POINTER_FLAG_UP;
        # both POINTER_FLAG_PRIMARY.
        for flags in (0x00012006, 0x00042000):
            info = _POINTER_TYPE_INFO(type=2)
            info.touchInfo.pointerInfo.pointerType = 2
            info.touchInfo.pointerInfo.pointerFlags = flags
            info.touchInfo.pointerInfo.ptPixelLocation = point
            assert user32.InjectSyntheticPointerInput(device, ctypes.byref(info), 1)
            time.sleep(0.05)
        time.sleep(0.5)
    finally:
        user32.DestroySyntheticPointerDevice(device)

    # As in a windowed WebView2: a touch, not the mouse Windows makes of it,
    # at (50, 50) in physical pixels, which the page has in CSS pixels.
    pointer = window.evaluate_js('window.touch')
    assert pointer is not None, 'the page got no pointerdown'
    kind, x, y = pointer
    expected = 50 / window.evaluate_js('window.devicePixelRatio')
    assert kind == 'touch'
    assert abs(x - expected) < 1
    assert abs(y - expected) < 1
