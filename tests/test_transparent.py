"""
Check transparent windows on Windows by reading screen pixels.

A transparent window is placed on top of an opaque magenta window. Its page paints the top-left
quadrant green and leaves the rest transparent, so the screen must show green in that quadrant
and magenta in the bottom-right one, along the top edge of the client area and, for a frameless
window, at the top of the window rectangle. A white tint shows up in the green channel of magenta.

The tests need an interactive, unlocked desktop with nothing covering the windows.
"""

import ctypes
import os
import sys
import threading
import time

import pytest

import webview

from .util import run_test

pytestmark = pytest.mark.skipif(
    sys.platform != 'win32' or os.environ.get('PYWEBVIEW_GUI', 'edgechromium') != 'edgechromium',
    reason='transparency is checked only on WinForms with EdgeChromium',
)

BACKGROUND_COLOR = (255, 0, 255)
OPAQUE_COLOR = (0, 160, 0)
TOLERANCE = 4

TRANSPARENT_TITLE = 'pywebview transparency test'
TRANSPARENT_HTML = """
<html>
<head>
<style>
    html, body { margin: 0; height: 100%; background: transparent; }
    #opaque { position: absolute; left: 0; top: 0; width: 50%; height: 50%;
              background: rgb(0, 160, 0); }
</style>
</head>
<body><div id="opaque"></div></body>
</html>
"""

DWMWA_SYSTEMBACKDROP_TYPE = 38
DWMSBT_MAINWINDOW = 2
HWND_BROADCAST = 0xFFFF
WM_SETTINGCHANGE = 0x001A
SMTO_ABORTIFHUNG = 0x0002


@pytest.fixture
def background_window():
    # Frameless and larger than the transparent window, so its client area covers it fully
    return webview.create_window(
        'pywebview transparency background',
        html='<html><body style="margin: 0; background: #ff00ff"></body></html>',
        background_color='#FF00FF',
        frameless=True,
        x=100,
        y=100,
        width=460,
        height=360,
    )


@pytest.mark.parametrize('frameless', [True, False])
def test_transparent(background_window, frameless):
    run_test(webview, background_window, check_transparency, param=(frameless, None))


def test_transparent_theme_change(background_window, monkeypatch):
    # Regression test for #1887: a dark theme change must not make the window opaque
    run_test(webview, background_window, check_transparency, param=(True, monkeypatch))


def check_transparency(_, frameless, monkeypatch):
    window = webview.create_window(
        TRANSPARENT_TITLE,
        html=TRANSPARENT_HTML,
        transparent=True,
        frameless=frameless,
        on_top=True,
        x=150,
        y=150,
        width=360,
        height=260,
    )
    try:
        assert window.events.loaded.wait(20), 'transparent window did not load'
        assert window.gui.renderer == 'edgechromium'
        hwnd = find_window(TRANSPARENT_TITLE)
        assert_colors(hwnd, frameless)

        if monkeypatch:
            simulate_dark_theme_change(window, monkeypatch)
            backdrop = get_backdrop_type(hwnd)
            if backdrop is not None:  # the attribute needs Windows 11 22H2
                assert backdrop != DWMSBT_MAINWINDOW, 'Mica backdrop set on a transparent window'
            assert_colors(hwnd, frameless)
    finally:
        window.destroy()


def simulate_dark_theme_change(window, monkeypatch):
    """
    Report the dark theme to the window and send the WM_SETTINGCHANGE broadcast that Windows sends
    on a theme change or after unlocking. The broadcast reaches every top-level window.
    """
    handled = threading.Event()

    def is_dark_theme(self):
        handled.set()
        return True

    monkeypatch.setattr(type(window.native), 'is_dark_theme', is_dark_theme)

    user32 = ctypes.windll.user32
    user32.SendMessageTimeoutW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.c_size_t,
        ctypes.c_wchar_p,
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    result = ctypes.c_size_t()
    user32.SendMessageTimeoutW(
        HWND_BROADCAST,
        WM_SETTINGCHANGE,
        0,
        'ImmersiveColorSet',
        SMTO_ABORTIFHUNG,
        2000,
        ctypes.byref(result),
    )

    assert handled.wait(5), 'the theme change handler did not run'
    time.sleep(0.5)  # let the handler finish and DWM compose a new frame


def find_window(title):
    user32 = ctypes.windll.user32
    user32.FindWindowW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
    user32.FindWindowW.restype = ctypes.c_void_p

    for _ in range(50):
        hwnd = user32.FindWindowW(None, title)
        if hwnd:
            return hwnd
        time.sleep(0.1)

    raise AssertionError(f'window {title!r} not found')


def assert_colors(hwnd, frameless, timeout=5):
    """Wait until every sample point shows the expected color."""
    samples = get_samples(hwnd, frameless)
    deadline = time.monotonic() + timeout

    while True:
        colors = {name: get_pixel(*point) for name, (point, _) in samples.items()}
        wrong = [
            f'{name} at {point} is {colors[name]}, expected {expected}'
            for name, (point, expected) in samples.items()
            if not is_close(colors[name], expected)
        ]
        if not wrong:
            return

        if time.monotonic() > deadline:
            raise AssertionError('; '.join(wrong))
        time.sleep(0.2)


def get_samples(hwnd, frameless):
    """Return a dict of sample names to (screen point, expected color)."""
    user32 = ctypes.windll.user32
    user32.GetClientRect.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    user32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    user32.ClientToScreen.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

    class RECT(ctypes.Structure):
        _fields_ = [(name, ctypes.c_long) for name in ('left', 'top', 'right', 'bottom')]

    class POINT(ctypes.Structure):
        _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]

    rect = RECT()
    window_rect = RECT()
    origin = POINT(0, 0)
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    user32.GetWindowRect(hwnd, ctypes.byref(window_rect))
    user32.ClientToScreen(hwnd, ctypes.byref(origin))
    width, height = rect.right, rect.bottom
    right_x = origin.x + 3 * width // 4

    samples = {
        'opaque area': ((origin.x + width // 4, origin.y + height // 4), OPAQUE_COLOR),
        'transparent area': ((right_x, origin.y + 3 * height // 4), BACKGROUND_COLOR),
        'top edge of the client area': ((right_x, origin.y + 2), BACKGROUND_COLOR),
    }
    if frameless:
        # Between the top of the window rectangle and the client area, if there is a frame
        top = (window_rect.top + max(origin.y, window_rect.top + 2)) // 2
        samples['top of the window'] = ((right_x, top), BACKGROUND_COLOR)

    return samples


def get_pixel(x, y):
    """Read a pixel of the composed screen as an (r, g, b) tuple."""
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    user32.GetDC.argtypes = [ctypes.c_void_p]
    user32.GetDC.restype = ctypes.c_void_p
    user32.ReleaseDC.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    gdi32.GetPixel.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
    gdi32.GetPixel.restype = ctypes.c_uint32

    hdc = user32.GetDC(None)
    try:
        color = gdi32.GetPixel(hdc, x, y)
    finally:
        user32.ReleaseDC(None, hdc)

    return color & 0xFF, (color >> 8) & 0xFF, (color >> 16) & 0xFF


def get_backdrop_type(hwnd):
    """Return DWMWA_SYSTEMBACKDROP_TYPE, or None where Windows does not support it."""
    dwmapi = ctypes.windll.dwmapi
    dwmapi.DwmGetWindowAttribute.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.c_void_p,
        ctypes.c_uint,
    ]
    value = ctypes.c_int()
    hr = dwmapi.DwmGetWindowAttribute(
        hwnd, DWMWA_SYSTEMBACKDROP_TYPE, ctypes.byref(value), ctypes.sizeof(value)
    )
    return value.value if hr == 0 else None


def is_close(color, expected):
    return all(abs(a - b) <= TOLERANCE for a, b in zip(color, expected))
