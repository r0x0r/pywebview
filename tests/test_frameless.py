import ctypes
import os
import sys
import time
from types import SimpleNamespace

import pytest

import webview

from .util import run_test

HTML = '<html><body><div class="pywebview-drag-region">title</div></body></html>'

# The resize handles are the only elements injected with the maximum z-index.
HANDLE_COUNT_JS = (
    "[...document.querySelectorAll('div')].filter((d) => d.style.zIndex === '2147483647').length"
)

GWL_STYLE = -16
WS_THICKFRAME = 0x00040000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
WS_SYSMENU = 0x00080000
NATIVE_FRAME = WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU

winforms_only = pytest.mark.skipif(
    sys.platform != 'win32' or os.environ.get('PYWEBVIEW_GUI') not in (None, '', 'winforms'),
    reason='the frameless window frame is implemented by the WinForms backend',
)


def _frame_state(window):
    """Window styles, window and client rect, monitor work area. All in physical pixels."""
    from ctypes import wintypes

    class Rect(wintypes.RECT):
        pass

    class MonitorInfo(ctypes.Structure):
        _fields_ = [
            ('cbSize', wintypes.DWORD),
            ('rcMonitor', Rect),
            ('rcWork', Rect),
            ('dwFlags', wintypes.DWORD),
        ]

    user32 = ctypes.windll.user32
    hwnd = int(window.native.Handle.ToInt32())

    window_rect = Rect()
    user32.GetWindowRect(hwnd, ctypes.byref(window_rect))

    client = Rect()
    user32.GetClientRect(hwnd, ctypes.byref(client))
    corners = [
        wintypes.POINT(client.left, client.top),
        wintypes.POINT(client.right, client.bottom),
    ]
    for corner in corners:
        user32.ClientToScreen(hwnd, ctypes.byref(corner))

    monitor = user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
    info = MonitorInfo()
    info.cbSize = ctypes.sizeof(MonitorInfo)
    assert user32.GetMonitorInfoW(monitor, ctypes.byref(info)), 'failed to read the monitor info'

    return SimpleNamespace(
        hwnd=hwnd,
        styles=user32.GetWindowLongW(hwnd, GWL_STYLE) & 0xFFFFFFFF,
        window=(window_rect.left, window_rect.top, window_rect.right, window_rect.bottom),
        client=(corners[0].x, corners[0].y, corners[1].x, corners[1].y),
        work_area=(info.rcWork.left, info.rcWork.top, info.rcWork.right, info.rcWork.bottom),
    )


@pytest.fixture
def keep_frame_styles():
    """
    Turn the setting on for one test, on the dictionary the backend reads.

    conftest.py reloads webview between tests, which replaces webview.settings,
    while the already imported platform module keeps its original binding. The
    value is restored afterwards so it cannot leak into the next test.
    """
    from webview.platforms import winforms

    previous = winforms.settings['KEEP_FRAME_STYLES']
    winforms.settings['KEEP_FRAME_STYLES'] = True
    yield
    winforms.settings['KEEP_FRAME_STYLES'] = previous


@winforms_only
def test_frameless():
    window = webview.create_window('Frameless test', 'https://www.example.org', frameless=True)
    run_test(webview, window)


@winforms_only
def test_custom_frame_is_off_by_default():
    """
    Swallowing WM_NCCALCSIZE takes the non-client area away from anything else that
    renders there, so the frame is restored only when it is asked for.
    """
    window = webview.create_window('Frameless test', html=HTML, frameless=True)

    def thread_func(_window):
        from webview.platforms import win32

        state = _frame_state(window)
        assert state.hwnd not in win32._custom_frames, 'the window procedure was subclassed'
        assert not state.styles & WS_THICKFRAME, 'the resize border was restored unprompted'

    run_test(webview, window, thread_func)


@winforms_only
def test_custom_frame_restores_the_native_window_styles(keep_frame_styles):
    """
    Without these styles the window is not managed as a window: it cannot be snapped
    to a screen edge by keyboard or by dragging, and it maximizes over the taskbar.
    """
    window = webview.create_window('Frameless test', html=HTML, frameless=True)

    def thread_func(_window):
        from webview.platforms import win32

        state = _frame_state(window)
        missing = NATIVE_FRAME & ~state.styles
        assert not missing, f'window styles are missing 0x{missing:x}'
        assert state.hwnd in win32._custom_frames, 'the window procedure was not subclassed'

    run_test(webview, window, thread_func)


@winforms_only
def test_maximized_window_matches_the_work_area(keep_frame_styles):
    """
    WM_GETMINMAXINFO declares the maximized geometry that the shell acts on. A window
    that only looks maximized - client clamped, window rect still overflowing the
    monitor by the resize border - disagrees with Win+Up, Win+Left and Aero Shake.
    """
    window = webview.create_window('Frameless test', html=HTML, frameless=True)

    def thread_func(_window):
        window.maximize()
        assert window.events.maximized.wait(5), 'the window was not maximized'
        time.sleep(0.5)  # let DWM settle the maximized bounds

        state = _frame_state(window)
        assert state.window == state.work_area, (
            f'maximized window rect {state.window} does not match the work area {state.work_area}'
        )
        assert state.client == state.work_area, (
            f'maximized client {state.client} does not match the work area {state.work_area}'
        )

        window.restore()
        assert window.events.restored.wait(5), 'the window was not restored'
        assert _frame_state(window).client != state.work_area, 'the client kept the maximized area'

    run_test(webview, window, thread_func)


@winforms_only
def test_custom_frame_survives_a_fullscreen_toggle(keep_frame_styles):
    """
    Leaving fullscreen assigns FormBorderStyle back, which rewrites the window
    styles the custom frame had restored.
    """
    window = webview.create_window('Frameless test', html=HTML, frameless=True)

    def thread_func(_window):
        window.toggle_fullscreen()
        time.sleep(1)
        window.toggle_fullscreen()
        time.sleep(1)

        missing = NATIVE_FRAME & ~_frame_state(window).styles
        assert not missing, f'window styles are missing 0x{missing:x} after leaving fullscreen'

    run_test(webview, window, thread_func)


@winforms_only
def test_drag_region_takes_precedence_over_the_resize_handle():
    """
    A title bar that reaches the top of the window sits under the top resize
    handle. Grabbing it there has to move the window, not resize it.
    """
    html = (
        '<html><body style="margin:0">'
        '<div class="pywebview-drag-region" style="height:40px"></div>'
        '</body></html>'
    )
    window = webview.create_window('Frameless test', html=html, frameless=True, easy_drag=False)

    def thread_func(_window):
        calls = window.evaluate_js(
            """
            (() => {
                const recorded = [];
                const original = window.pywebview._jsApiCallback;
                window.pywebview._jsApiCallback = (name) => recorded.push(name);

                const onTitle = document.elementFromPoint(100, 2);
                onTitle.dispatchEvent(new MouseEvent('mousedown',
                    {bubbles: true, button: 0, clientX: 100, clientY: 2}));

                const onBottom = document.elementFromPoint(100, window.innerHeight - 2);
                onBottom.dispatchEvent(new MouseEvent('mousedown',
                    {bubbles: true, button: 0, clientX: 100, clientY: window.innerHeight - 2}));

                window.pywebview._jsApiCallback = original;
                return JSON.stringify(recorded);
            })()
            """
        )
        assert calls == '["pywebviewStartDrag","pywebviewStartResize"]', f'got {calls}'

    run_test(webview, window, thread_func)


@winforms_only
def test_resize_handles_are_injected():
    """
    A frameless window cannot hit-test its own edges - the points over the page
    reach the webview child window first - so the page carries the handles.
    """
    window = webview.create_window('Frameless test', html=HTML, frameless=True)

    def thread_func(_window):
        count = window.evaluate_js(HANDLE_COUNT_JS)
        assert count == 8, f'expected 8 resize handles, got {count}'

    run_test(webview, window, thread_func)


@winforms_only
def test_resize_handles_are_not_injected_for_normal_windows():
    window = webview.create_window('Frameless test', html=HTML, frameless=False)

    def thread_func(_window):
        count = window.evaluate_js(HANDLE_COUNT_JS)
        assert count == 0, f'expected no resize handles, got {count}'

    run_test(webview, window, thread_func)


@winforms_only
def test_resize_handles_are_not_injected_for_fixed_size_windows():
    window = webview.create_window('Frameless test', html=HTML, frameless=True, resizable=False)

    def thread_func(_window):
        count = window.evaluate_js(HANDLE_COUNT_JS)
        assert count == 0, f'expected no resize handles, got {count}'

        styles = _frame_state(window).styles
        assert not styles & WS_THICKFRAME, 'a fixed size window must not keep a resize border'

    run_test(webview, window, thread_func)
