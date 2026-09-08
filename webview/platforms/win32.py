import ctypes
import logging as _logging
import os
from ctypes import wintypes

from webview.util import parse_file_type

_log = _logging.getLogger('pywebview')

_WM_MOUSEWHEEL = 0x020A
_WM_MOUSEHWHEEL = 0x020E
_WM_MOUSEMOVE = 0x0200
_WM_LBUTTONUP = 0x0202
_WM_NCLBUTTONDOWN = 0x00A1
_HT_CAPTION = 0x0002
_WH_MOUSE_LL = 14
_SWP_NOSIZE = 0x0001
_SWP_NOZORDER = 0x0004
_SWP_NOACTIVATE = 0x0010
_VK_LBUTTON = 0x01
_VK_RBUTTON = 0x02
_VK_MBUTTON = 0x04
_VK_XBUTTON1 = 0x05
_VK_XBUTTON2 = 0x06
_VK_SHIFT = 0x10
_VK_CONTROL = 0x11
_SW_RESTORE = 9
_DRAG_TOLERANCE = 5  # px; suppresses accidental micro-drags on click

# WM_(H)MOUSEWHEEL wParam low-word modifier/button flags
_MK_LBUTTON = 0x0001
_MK_RBUTTON = 0x0002
_MK_SHIFT = 0x0004
_MK_CONTROL = 0x0008
_MK_MBUTTON = 0x0010
_MK_XBUTTON1 = 0x0020
_MK_XBUTTON2 = 0x0040

# Window-style constants used by frameless-window setup.
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000


class _MSLLHOOKSTRUCT(ctypes.Structure):
    # https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-msllhookstruct
    _fields_ = [
        ('pt_x', wintypes.LONG),
        ('pt_y', wintypes.LONG),
        ('mouseData', wintypes.DWORD),  # HIWORD = wheel delta for WM_MOUSEWHEEL
        ('flags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', ctypes.c_size_t),
    ]


_user32 = ctypes.windll.user32
_user32.SetWindowsHookExW.restype = ctypes.c_void_p
_user32.SetWindowsHookExW.argtypes = [
    ctypes.c_int,
    ctypes.c_void_p,
    ctypes.c_void_p,
    wintypes.DWORD,
]
_user32.UnhookWindowsHookEx.restype = wintypes.BOOL
_user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
_user32.CallNextHookEx.restype = ctypes.c_ssize_t
_user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
_user32.PostMessageW.restype = wintypes.BOOL
_user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
_user32.WindowFromPoint.restype = wintypes.HWND
_user32.WindowFromPoint.argtypes = [wintypes.POINT]
_user32.IsChild.restype = wintypes.BOOL
_user32.IsChild.argtypes = [wintypes.HWND, wintypes.HWND]
_user32.GetCursorPos.restype = wintypes.BOOL
_user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
_user32.EnumChildWindows.restype = wintypes.BOOL
_user32.EnumChildWindows.argtypes = [wintypes.HWND, ctypes.c_void_p, wintypes.LPARAM]
_user32.GetClassNameW.restype = ctypes.c_int
_user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
_user32.ReleaseCapture.restype = wintypes.BOOL
_user32.ReleaseCapture.argtypes = []
_user32.SendMessageW.restype = ctypes.c_ssize_t
_user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
_user32.IsZoomed.restype = wintypes.BOOL
_user32.IsZoomed.argtypes = [wintypes.HWND]
_user32.GetWindowRect.restype = wintypes.BOOL
_user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
# Available since Windows 8.1 – converts physical screen px to process-logical px.
# This module is imported for every WinForms renderer, including MSHTML (the
# fallback documented to work on Windows 7), so the lookup must not raise if
# it's missing there.
_PhysicalToLogicalPointForPerMonitorDPI = getattr(
    _user32, 'PhysicalToLogicalPointForPerMonitorDPI', None
)
if _PhysicalToLogicalPointForPerMonitorDPI is not None:
    _PhysicalToLogicalPointForPerMonitorDPI.restype = wintypes.BOOL
    _PhysicalToLogicalPointForPerMonitorDPI.argtypes = [
        wintypes.HWND,
        ctypes.POINTER(wintypes.POINT),
    ]
_user32.SetWindowPos.restype = wintypes.BOOL
_user32.SetWindowPos.argtypes = [
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
]
_user32.GetKeyState.restype = wintypes.SHORT
_user32.GetKeyState.argtypes = [ctypes.c_int]
_user32.ShowWindow.restype = wintypes.BOOL
_user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
_user32.MonitorFromRect.restype = wintypes.HANDLE
_user32.MonitorFromRect.argtypes = [ctypes.POINTER(wintypes.RECT), wintypes.DWORD]
_user32.GetMonitorInfoW.restype = wintypes.BOOL
_user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
_user32.EnumDisplaySettingsW.restype = wintypes.BOOL
_user32.EnumDisplaySettingsW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p]
if hasattr(_user32, 'GetThreadDpiAwarenessContext'):
    _user32.GetThreadDpiAwarenessContext.restype = ctypes.c_void_p
    _user32.GetThreadDpiAwarenessContext.argtypes = []
    _user32.GetAwarenessFromDpiAwarenessContext.restype = ctypes.c_int
    _user32.GetAwarenessFromDpiAwarenessContext.argtypes = [ctypes.c_void_p]

_LowLevelMouseProcType = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, ctypes.c_void_p
)
_EnumChildProcType = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

# hwnd → drag state list registered by install_mouse_hook.
# start_drag() uses this to choose the hook-based path for WinUI3.
_drag_states: dict[int, list] = {}


def _mouse_wheel_key_state() -> int:
    """Build the WM_(H)MOUSEWHEEL wParam low word (MK_* flags) from live key/button state."""
    flags = 0
    for vk, mk in (
        (_VK_CONTROL, _MK_CONTROL),
        (_VK_SHIFT, _MK_SHIFT),
        (_VK_LBUTTON, _MK_LBUTTON),
        (_VK_RBUTTON, _MK_RBUTTON),
        (_VK_MBUTTON, _MK_MBUTTON),
        (_VK_XBUTTON1, _MK_XBUTTON1),
        (_VK_XBUTTON2, _MK_XBUTTON2),
    ):
        if _user32.GetAsyncKeyState(vk) & 0x8000:
            flags |= mk
    return flags


def _find_input_hwnd(parent_hwnd: int) -> int | None:
    """
    Find the WebView2 input HWND under parent_hwnd.

    The XAML WebView2 uses compositor hosting, so there is no
    Chrome_RenderWidgetHostHWND.  The actual input window is Chrome_WidgetWin_0.
    Search priority: Chrome_RenderWidgetHostHWND > Chrome_WidgetWin_0 > Chrome_WidgetWin_1
    """
    _PRIORITY = {
        'Chrome_RenderWidgetHostHWND': 0,
        'Chrome_WidgetWin_0': 1,
        'Chrome_WidgetWin_1': 2,
    }
    result = []

    @_EnumChildProcType
    def callback(hwnd, _):
        buf = ctypes.create_unicode_buffer(256)
        _user32.GetClassNameW(hwnd, buf, 256)
        if buf.value in _PRIORITY:
            result.append((hwnd, buf.value))
        return True

    _user32.EnumChildWindows(parent_hwnd, callback, 0)

    if not result:
        return None
    result.sort(key=lambda item: _PRIORITY[item[1]])
    return result[0][0]


def install_mouse_hook(hwnd: int):
    """
    Install a WH_MOUSE_LL (low-level mouse) hook that intercepts
    WM_MOUSEWHEEL / WM_MOUSEHWHEEL system-wide and forwards them to the
    WebView2 input HWND so that XAML cannot swallow them.

    The hook also implements frameless-window dragging via SetWindowPos
    (activated by :func:`start_drag`).

    Returns ``(hook_proc, hook_handle)``; the caller must keep references
    to both to prevent GC.
    """
    hook_handle: list = [None]
    # Use a list with a sentinel so we distinguish "not yet searched" (None)
    # from "searched and not found" (0).
    input_hwnd_cache: list = [None]
    # Drag state: [active, cursor_start_x, cursor_start_y, win_start_x, win_start_y, was_zoomed, max_win_width]
    # active: 0=inactive, 1=dragging, 2=pending (within tolerance)
    _drag: list = [0, 0, 0, 0, 0, 0, 0]
    _drag_states[hwnd] = _drag

    def _get_input_hwnd() -> int | None:
        if input_hwnd_cache[0] is None:
            found = _find_input_hwnd(hwnd)
            if found:
                input_hwnd_cache[0] = found
        return input_hwnd_cache[0]

    @_LowLevelMouseProcType
    def hook_proc(nCode, wParam, lParam):
        if nCode >= 0 and lParam:
            # ── Window drag ──────────────────────────────────────────
            if _drag[0]:
                if wParam == _WM_LBUTTONUP:
                    _drag[0] = 0
                elif wParam == _WM_MOUSEMOVE:
                    # MSLLHOOKSTRUCT.pt is in per-monitor physical pixels; convert to
                    # logical so it matches GetWindowRect / SetWindowPos coordinates.
                    # Do NOT suppress (return 1) — suppressing prevents the OS from
                    # committing the cursor position, causing oscillation on every move.
                    hs = ctypes.cast(
                        ctypes.c_void_p(lParam), ctypes.POINTER(_MSLLHOOKSTRUCT)
                    ).contents
                    pt = wintypes.POINT(hs.pt_x, hs.pt_y)
                    if _PhysicalToLogicalPointForPerMonitorDPI is not None:
                        _PhysicalToLogicalPointForPerMonitorDPI(hwnd, ctypes.byref(pt))
                        # Pre-8.1: no per-monitor DPI concept, physical == logical.
                    if _drag[0] == 2:  # pending — promote to active once tolerance exceeded
                        dx = pt.x - _drag[1]
                        dy = pt.y - _drag[2]
                        if dx * dx + dy * dy >= _DRAG_TOLERANCE * _DRAG_TOLERANCE:
                            if _drag[5]:  # restore maximized window now that drag is confirmed
                                # Remember how far the cursor was from the window origin
                                # when the drag started (in the maximized state).
                                cursor_off_x = _drag[1] - _drag[3]
                                cursor_off_y = _drag[2] - _drag[4]
                                max_width = _drag[6] if _drag[6] > 0 else 1

                                _user32.ShowWindow(hwnd, _SW_RESTORE)
                                rect = wintypes.RECT()
                                _user32.GetWindowRect(hwnd, ctypes.byref(rect))
                                restored_width = rect.right - rect.left

                                # Place the window so the cursor sits at the same
                                # relative horizontal position in the title bar.
                                new_x = pt.x - int(cursor_off_x / max_width * restored_width)
                                new_y = pt.y - cursor_off_y

                                _drag[1] = pt.x
                                _drag[2] = pt.y
                                _drag[3] = new_x
                                _drag[4] = new_y
                            _drag[0] = 1
                    if _drag[0] == 1:
                        _user32.SetWindowPos(
                            hwnd,
                            0,
                            _drag[3] + pt.x - _drag[1],
                            _drag[4] + pt.y - _drag[2],
                            0,
                            0,
                            _SWP_NOSIZE | _SWP_NOZORDER | _SWP_NOACTIVATE,
                        )
                    # fall through so the OS commits the cursor position

            # ── Mouse-wheel forwarding ───────────────────────────────
            if wParam in (_WM_MOUSEWHEEL, _WM_MOUSEHWHEEL):
                hs = ctypes.cast(ctypes.c_void_p(lParam), ctypes.POINTER(_MSLLHOOKSTRUCT)).contents

                # MSLLHOOKSTRUCT.pt is in physical (per-monitor DPI-aware) pixels.
                # GetCursorPos + WindowFromPoint both use the process's logical space,
                # avoiding mismatches on HiDPI displays (e.g. Retina Mac via Parallels).
                logical_pt = wintypes.POINT()
                _user32.GetCursorPos(ctypes.byref(logical_pt))
                window_at_cursor = _user32.WindowFromPoint(logical_pt)
                over_our_window = window_at_cursor and (
                    window_at_cursor == hwnd or _user32.IsChild(hwnd, window_at_cursor)
                )
                if over_our_window:
                    # Forward only while the pointer is inside Chromium's input
                    # surface, not over XAML menus, title bars, or native chrome.
                    target = _get_input_hwnd()
                    if target:
                        target_rect = wintypes.RECT()
                        if not _user32.GetWindowRect(target, ctypes.byref(target_rect)) or not (
                            target_rect.left <= logical_pt.x < target_rect.right
                            and target_rect.top <= logical_pt.y < target_rect.bottom
                        ):
                            return _user32.CallNextHookEx(hook_handle[0], nCode, wParam, lParam)
                    elif window_at_cursor != hwnd:
                        # Before Chromium exposes its input HWND, retain the
                        # compositor-hosting fallback for child content only.
                        target = window_at_cursor
                    else:
                        return _user32.CallNextHookEx(hook_handle[0], nCode, wParam, lParam)

                    lparam = ((logical_pt.y & 0xFFFF) << 16) | (logical_pt.x & 0xFFFF)
                    # HIWORD(mouseData) carries the wheel delta; the low word must
                    # carry the current MK_* modifier/button flags, not mouseData's
                    # (always-zero) low word, so Ctrl/Shift+wheel behave correctly.
                    wheel_wparam = (hs.mouseData & 0xFFFF0000) | _mouse_wheel_key_state()
                    _user32.PostMessageW(target, wParam, wheel_wparam, lparam)
                    return 1  # suppress original so XAML doesn't swallow it

        return _user32.CallNextHookEx(hook_handle[0], nCode, wParam, lParam)

    # WH_MOUSE_LL is a global hook — pass thread_id=0, no DLL required.
    hook_handle[0] = _user32.SetWindowsHookExW(_WH_MOUSE_LL, hook_proc, None, 0)
    if not hook_handle[0]:
        _log.error('Failed to install mouse hook for hwnd=0x%x', hwnd)
        _drag_states.pop(hwnd, None)
    return hook_proc, hook_handle[0]


def uninstall_mouse_hook(hwnd: int, hook: 'tuple | None') -> None:
    """Reverse :func:`install_mouse_hook`.

    ``hook`` is the tuple returned by ``install_mouse_hook``; pass ``None`` to
    skip unhooking when the hook failed to install.
    """
    _drag_states.pop(hwnd, None)
    if not hook:
        return
    _, hook_handle = hook
    if hook_handle and not _user32.UnhookWindowsHookEx(hook_handle):
        _log.warning('UnhookWindowsHookEx failed for hwnd=0x%x', hwnd)


def start_drag(hwnd: int) -> None:
    """Initiate a native window drag (title-bar grab) via Win32.

    For hwnds with a mouse hook installed (WinUI3), the drag is handled
    inside the hook using SetWindowPos. For other hwnds (WinForms), the
    standard ReleaseCapture / WM_NCLBUTTONDOWN approach is used.
    """
    # Only start drag if left mouse button is pressed
    if not (_user32.GetKeyState(_VK_LBUTTON) & 0x8000):
        return

    drag = _drag_states.get(hwnd)
    if drag is not None:
        rect = wintypes.RECT()
        _user32.GetWindowRect(hwnd, ctypes.byref(rect))
        cursor = wintypes.POINT()
        _user32.GetCursorPos(ctypes.byref(cursor))
        drag[0] = 2  # pending — move only after tolerance exceeded
        drag[1] = cursor.x
        drag[2] = cursor.y
        drag[3] = rect.left
        drag[4] = rect.top
        drag[5] = 1 if _user32.IsZoomed(hwnd) else 0
        drag[6] = rect.right - rect.left  # maximized window width for proportional restore
    else:
        # WM_NCLBUTTONDOWN causes the OS to restore-and-drag a maximized window.
        _user32.ReleaseCapture()
        _user32.SendMessageW(hwnd, _WM_NCLBUTTONDOWN, _HT_CAPTION, 0)


class _MONITORINFOEX(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.DWORD),
        ('rcMonitor', wintypes.RECT),
        ('rcWork', wintypes.RECT),
        ('dwFlags', wintypes.DWORD),
        ('szDevice', wintypes.WCHAR * 32),
    ]


class _DEVMODE(ctypes.Structure):
    _fields_ = [
        ('dmDeviceName', wintypes.WCHAR * 32),
        ('dmSpecVersion', wintypes.WORD),
        ('dmDriverVersion', wintypes.WORD),
        ('dmSize', wintypes.WORD),
        ('dmDriverExtra', wintypes.WORD),
        ('dmFields', wintypes.DWORD),
        ('dmPositionX', wintypes.LONG),
        ('dmPositionY', wintypes.LONG),
        ('dmDisplayOrientation', wintypes.DWORD),
        ('dmDisplayFixedOutput', wintypes.DWORD),
        ('dmColor', wintypes.SHORT),
        ('dmDuplex', wintypes.SHORT),
        ('dmYResolution', wintypes.SHORT),
        ('dmTTOption', wintypes.SHORT),
        ('dmCollate', wintypes.SHORT),
        ('dmFormName', wintypes.WCHAR * 32),
        ('dmLogPixels', wintypes.WORD),
        ('dmBitsPerPel', wintypes.DWORD),
        ('dmPelsWidth', wintypes.DWORD),
        ('dmPelsHeight', wintypes.DWORD),
        ('dmDisplayFlags', wintypes.DWORD),
        ('dmDisplayFrequency', wintypes.DWORD),
        ('dmICMMethod', wintypes.DWORD),
        ('dmICMIntent', wintypes.DWORD),
        ('dmMediaType', wintypes.DWORD),
        ('dmDitherType', wintypes.DWORD),
        ('dmReserved1', wintypes.DWORD),
        ('dmReserved2', wintypes.DWORD),
        ('dmPanningWidth', wintypes.DWORD),
        ('dmPanningHeight', wintypes.DWORD),
    ]


def get_monitor_scale(x: int, y: int, width: int, height: int) -> float:
    """
    Get the DPI scale factor for the monitor containing the given rectangle.

    Two independent methods are available because the correct one depends on
    the calling thread's DPI-awareness context:

    * **System-DPI-aware** (WinForms): ``GetDpiForMonitor`` returns 96
      regardless of actual scaling, but ``rcMonitor`` from
      ``GetMonitorInfoW`` is in logical pixels so the physical/logical ratio
      gives the correct scale.
    * **Per-monitor-DPI-aware** (WinUI3 / WinRT threads): ``rcMonitor`` is
      in physical pixels (ratio = 1.0) but ``GetDpiForMonitor`` returns the
      real DPI.

    The thread's DPI-awareness context selects the result. This matters when a
    secondary monitor has a lower scale than the primary monitor: taking the
    maximum would incorrectly retain the primary monitor's system DPI.

    The coordinates can be in either logical or physical pixels —
    ``MonitorFromRect`` with ``MONITOR_DEFAULTTONEAREST`` will resolve to the
    correct monitor in both cases.

    Returns:
        The scale factor (e.g., 1.0, 1.5, 2.0, etc.)
    """
    try:
        rect = wintypes.RECT(x, y, x + width, y + height)
        hmonitor = _user32.MonitorFromRect(ctypes.byref(rect), 2)  # MONITOR_DEFAULTTONEAREST
        if not hmonitor:
            return 1.0

        awareness = None
        try:
            context = _user32.GetThreadDpiAwarenessContext()
            awareness = _user32.GetAwarenessFromDpiAwarenessContext(context)
        except Exception:
            pass

        # Method 1: GetDpiForMonitor (works in per-monitor-DPI-aware contexts)
        scale_from_dpi = 1.0
        try:
            dpi_x = wintypes.UINT()
            dpi_y = wintypes.UINT()
            hr = ctypes.windll.shcore.GetDpiForMonitor(
                hmonitor, 0, ctypes.byref(dpi_x), ctypes.byref(dpi_y)
            )
            if hr == 0 and dpi_x.value > 0:
                scale_from_dpi = dpi_x.value / 96.0
        except Exception:
            pass

        # Method 2: physical / logical ratio (works in system-DPI-aware contexts)
        scale_from_ratio = 1.0
        try:
            mi = _MONITORINFOEX()
            mi.cbSize = ctypes.sizeof(_MONITORINFOEX)
            if _user32.GetMonitorInfoW(hmonitor, ctypes.byref(mi)):
                logical_width = mi.rcMonitor.right - mi.rcMonitor.left
                dm = _DEVMODE()
                dm.dmSize = ctypes.sizeof(_DEVMODE)
                if _user32.EnumDisplaySettingsW(mi.szDevice, -1, ctypes.byref(dm)):
                    if logical_width > 0:
                        scale_from_ratio = dm.dmPelsWidth / logical_width
        except Exception:
            pass

        # DPI_AWARENESS_PER_MONITOR_AWARE = 2. Unaware/system-aware callers
        # receive virtualized monitor bounds, so their physical/logical ratio
        # is authoritative; per-monitor-aware callers use the monitor DPI.
        if awareness == 2:
            return scale_from_dpi
        if awareness in (0, 1):
            return scale_from_ratio

        # Older Windows versions may not expose the awareness APIs. Prefer a
        # non-unit ratio because virtualized bounds indicate system awareness.
        return scale_from_ratio if scale_from_ratio != 1.0 else scale_from_dpi

    except Exception as e:
        _log.debug(f'Failed to get monitor scale: {e}')

    return 1.0


class _MARGINS(ctypes.Structure):
    _fields_ = [
        ('cxLeftWidth', ctypes.c_int),
        ('cxRightWidth', ctypes.c_int),
        ('cyTopHeight', ctypes.c_int),
        ('cyBottomHeight', ctypes.c_int),
    ]


def dwm_set_window_attribute(hwnd: int, attr: int, value: int, size: int = 4) -> int:
    dwm_set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
    dwm_set_window_attribute.argtypes = [
        wintypes.HWND,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    return dwm_set_window_attribute(hwnd, attr, ctypes.byref(ctypes.c_int(value)), size)


def extend_frame_into_client_area(hwnd: int) -> int:
    dwm_extend_frame_into_client_area = ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea
    m = _MARGINS(cxLeftWidth=1, cxRightWidth=1, cyTopHeight=1, cyBottomHeight=1)
    return dwm_extend_frame_into_client_area(hwnd, ctypes.byref(m))


def enable_window_shadow(hwnd: int) -> None:
    """
    Restore the native drop shadow on a window whose border/title bar has been
    removed (e.g. a frameless window), via the same DWM non-client-rendering
    trick used to give borderless WinForms windows a shadow.
    """
    extend_frame_into_client_area(hwnd)
    dwm_set_window_attribute(hwnd, 2, 2, 4)  # DWMWA_NCRENDERING_POLICY = DWMNCRP_ENABLED


class _GUID(ctypes.Structure):
    _fields_ = [
        ('Data1', wintypes.DWORD),
        ('Data2', wintypes.WORD),
        ('Data3', wintypes.WORD),
        ('Data4', ctypes.c_ubyte * 8),
    ]


def _guid(s: str) -> _GUID:
    s = s.strip('{}').replace('-', '')
    g = _GUID()
    g.Data1 = int(s[0:8], 16)
    g.Data2 = int(s[8:12], 16)
    g.Data3 = int(s[12:16], 16)
    for i, b in enumerate(bytes.fromhex(s[16:])):
        g.Data4[i] = b
    return g


_ole32 = ctypes.windll.ole32
_shell32 = ctypes.windll.shell32

_CLSID_FileOpenDialog = _guid('{DC1C5A9C-E88A-4dde-A5A1-60F82A20AEF7}')
_CLSID_FileSaveDialog = _guid('{C0B4E2F3-BA21-4773-8DBA-335EC946EB8B}')
_IID_IFileOpenDialog = _guid('{D57C7288-D4AD-4768-BE02-9D969532D960}')
_IID_IFileDialog = _guid('{42F85136-DB7E-439C-85F1-E4075D135FC8}')
_IID_IShellItem = _guid('{43826D1E-E718-42EE-BC55-A1E261C37BFE}')

_FOS_PICKFOLDERS = 0x00000020
_FOS_ALLOWMULTISELECT = 0x00000200
_FOS_FORCEFILESYSTEM = 0x00000040
_CLSCTX_INPROC_SERVER = 1
# (int)0x80058000 — the SIGDN_FILESYSPATH enum value
_SIGDN_FILESYSPATH = ctypes.c_int32(0x80058000).value
# HRESULT_FROM_WIN32(ERROR_CANCELLED) — user dismissed the dialog
_E_CANCELLED = ctypes.c_int32(0x800704C7).value
_HRESULT = ctypes.c_long

# IFileOpenDialog vtable indices
# IUnknown (0-2) + IModalWindow (3) + IFileDialog (4-26) + IFileOpenDialog (27-28)
_VTBL_RELEASE = 2  # IUnknown::Release
_VTBL_SHOW = 3  # IModalWindow::Show
_VTBL_SET_FILE_TYPES = 4  # IFileDialog::SetFileTypes
_VTBL_SET_OPTIONS = 9  # IFileDialog::SetOptions
_VTBL_GET_OPTIONS = 10  # IFileDialog::GetOptions
_VTBL_SET_FOLDER = 12  # IFileDialog::SetFolder
_VTBL_SET_FILE_NAME = 15  # IFileDialog::SetFileName
_VTBL_GET_RESULT = 20  # IFileDialog::GetResult
_VTBL_GET_RESULTS = 27  # IFileOpenDialog::GetResults
# IShellItemArray vtable indices (IUnknown 0-2 + own methods 3+)
_VTBL_SA_GET_COUNT = 7  # IShellItemArray::GetCount
_VTBL_SA_GET_ITEM = 8  # IShellItemArray::GetItemAt
# IShellItem vtable indices
_VTBL_SI_DISP_NAME = 5  # IShellItem::GetDisplayName


class _COMDLG_FILTERSPEC(ctypes.Structure):
    _fields_ = [('pszName', wintypes.LPCWSTR), ('pszSpec', wintypes.LPCWSTR)]


def _com_fn(obj, idx, restype, *argtypes):
    """Return the COM method at vtable[idx] as a callable."""
    vtbl = ctypes.cast(
        ctypes.cast(obj, ctypes.POINTER(ctypes.c_void_p))[0],
        ctypes.POINTER(ctypes.c_void_p),
    )
    return ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)(vtbl[idx])


def _com_release(obj):
    vtbl = ctypes.cast(
        ctypes.cast(obj, ctypes.POINTER(ctypes.c_void_p))[0],
        ctypes.POINTER(ctypes.c_void_p),
    )
    ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(vtbl[_VTBL_RELEASE])(obj)


def _check(hr) -> None:
    if hr:
        raise ctypes.WinError(ctypes.c_uint32(hr).value)


def _shell_item_from_path(path: str) -> ctypes.c_void_p | None:
    """Create an IShellItem for `path` via SHCreateItemFromParsingName."""
    item = ctypes.c_void_p()
    hr = _shell32.SHCreateItemFromParsingName(
        ctypes.c_wchar_p(path), None, ctypes.byref(_IID_IShellItem), ctypes.byref(item)
    )
    if hr:
        _log.warning('SHCreateItemFromParsingName(%r) failed: 0x%08x', path, hr)
        return None
    return item


def _set_dialog_folder(dialog, directory: str) -> None:
    """Set the initial folder shown by an IFileDialog, if it exists on disk."""
    if not directory or not os.path.isdir(directory):
        return

    item = _shell_item_from_path(directory)
    if item is None:
        return
    try:
        hr = _com_fn(dialog, _VTBL_SET_FOLDER, _HRESULT, ctypes.c_void_p)(dialog, item)
        if hr:
            _log.warning('IFileDialog::SetFolder(%r) failed: 0x%08x', directory, hr)
    finally:
        _com_release(item)


def _set_dialog_file_types(dialog, file_types: list[str]):
    """
    Apply pywebview `file_types` filter strings (e.g. 'Images (*.png;*.jpg)') to an
    IFileDialog. Returns the filter spec array, which must outlive the Show() call:
    IFileDialog retains the array pointer rather than copying it, so both the
    struct-array buffer itself and the string buffers its entries point to have
    to stay alive — assigning fields directly on the array (rather than copying
    in separately-built `_COMDLG_FILTERSPEC` instances) keeps ctypes' keepalive
    tracking anchored on the one object the caller is told to hold onto.
    """
    parsed = [parse_file_type(f) for f in file_types]
    if not parsed:
        return None

    array = (_COMDLG_FILTERSPEC * len(parsed))()
    for entry, (name, spec) in zip(array, parsed):
        entry.pszName = name
        entry.pszSpec = spec

    hr = _com_fn(
        dialog, _VTBL_SET_FILE_TYPES, _HRESULT, ctypes.c_uint32, ctypes.POINTER(_COMDLG_FILTERSPEC)
    )(dialog, len(array), array)
    if hr:
        _log.warning('IFileDialog::SetFileTypes failed: 0x%08x', hr)

    return array


def _shell_item_path(item) -> str | None:
    path_ptr = ctypes.c_void_p()
    hr = _com_fn(
        item, _VTBL_SI_DISP_NAME, _HRESULT, ctypes.c_int32, ctypes.POINTER(ctypes.c_void_p)
    )(item, _SIGDN_FILESYSPATH, ctypes.byref(path_ptr))
    if hr or not path_ptr.value:
        _log.warning('IShellItem::GetDisplayName failed: 0x%08x', hr)
        return None

    path = ctypes.wstring_at(path_ptr.value)
    _ole32.CoTaskMemFree(path_ptr)
    return path


def pick_folders_win32(
    hwnd: int, allow_multiple: bool = True, directory: str | None = None
) -> list[str] | None:
    """
    Show a folder-selection dialog via IFileOpenDialog (Win32 COM).

    Must be called on a COM-initialised (STA) thread.
    Returns a list of selected folder paths, or None if the user cancelled.
    """
    dialog = ctypes.c_void_p()
    _check(
        _ole32.CoCreateInstance(
            ctypes.byref(_CLSID_FileOpenDialog),
            None,
            _CLSCTX_INPROC_SERVER,
            ctypes.byref(_IID_IFileOpenDialog),
            ctypes.byref(dialog),
        )
    )

    try:
        options = ctypes.c_uint32()
        _check(
            _com_fn(dialog, _VTBL_GET_OPTIONS, _HRESULT, ctypes.POINTER(ctypes.c_uint32))(
                dialog, ctypes.byref(options)
            )
        )

        flags = options.value | _FOS_PICKFOLDERS | _FOS_FORCEFILESYSTEM
        if allow_multiple:
            flags |= _FOS_ALLOWMULTISELECT

        _check(_com_fn(dialog, _VTBL_SET_OPTIONS, _HRESULT, ctypes.c_uint32)(dialog, flags))

        if directory:
            _set_dialog_folder(dialog, directory)

        # Show() blocks, pumping its own message loop, until the dialog is dismissed.
        hr = _com_fn(dialog, _VTBL_SHOW, _HRESULT, wintypes.HWND)(dialog, hwnd)
        if hr == _E_CANCELLED:
            return None
        _check(hr)

        if not allow_multiple:
            item = ctypes.c_void_p()
            _check(
                _com_fn(dialog, _VTBL_GET_RESULT, _HRESULT, ctypes.POINTER(ctypes.c_void_p))(
                    dialog, ctypes.byref(item)
                )
            )
            try:
                path = _shell_item_path(item)
                return [path] if path is not None else None
            finally:
                _com_release(item)

        item_array = ctypes.c_void_p()
        _check(
            _com_fn(dialog, _VTBL_GET_RESULTS, _HRESULT, ctypes.POINTER(ctypes.c_void_p))(
                dialog, ctypes.byref(item_array)
            )
        )

        try:
            count = ctypes.c_uint32()
            _check(
                _com_fn(item_array, _VTBL_SA_GET_COUNT, _HRESULT, ctypes.POINTER(ctypes.c_uint32))(
                    item_array, ctypes.byref(count)
                )
            )

            paths: list[str] = []
            for i in range(count.value):
                item = ctypes.c_void_p()
                hr = _com_fn(
                    item_array,
                    _VTBL_SA_GET_ITEM,
                    _HRESULT,
                    ctypes.c_uint32,
                    ctypes.POINTER(ctypes.c_void_p),
                )(item_array, i, ctypes.byref(item))
                if hr:
                    _log.warning('IShellItemArray::GetItemAt(%d) failed: 0x%08x', i, hr)
                    continue
                try:
                    path = _shell_item_path(item)
                    if path is not None:
                        paths.append(path)
                finally:
                    _com_release(item)

            return paths
        finally:
            _com_release(item_array)
    finally:
        _com_release(dialog)


def pick_files_win32(
    hwnd: int,
    allow_multiple: bool,
    file_types: list[str],
    directory: str | None = None,
) -> list[str] | None:
    """
    Show an open-file dialog via IFileOpenDialog (Win32 COM), honoring an initial
    directory that the WinRT FileOpenPicker cannot express.

    Must be called on a COM-initialised (STA) thread.
    Returns a list of selected file paths, or None if the user cancelled.
    """
    dialog = ctypes.c_void_p()
    _check(
        _ole32.CoCreateInstance(
            ctypes.byref(_CLSID_FileOpenDialog),
            None,
            _CLSCTX_INPROC_SERVER,
            ctypes.byref(_IID_IFileOpenDialog),
            ctypes.byref(dialog),
        )
    )

    try:
        if allow_multiple:
            options = ctypes.c_uint32()
            _check(
                _com_fn(dialog, _VTBL_GET_OPTIONS, _HRESULT, ctypes.POINTER(ctypes.c_uint32))(
                    dialog, ctypes.byref(options)
                )
            )
            _check(
                _com_fn(dialog, _VTBL_SET_OPTIONS, _HRESULT, ctypes.c_uint32)(
                    dialog, options.value | _FOS_ALLOWMULTISELECT
                )
            )

        # kept alive until Show() returns: SetFileTypes reads these strings by pointer
        _filter_specs = _set_dialog_file_types(dialog, file_types) if file_types else None

        if directory:
            _set_dialog_folder(dialog, directory)

        hr = _com_fn(dialog, _VTBL_SHOW, _HRESULT, wintypes.HWND)(dialog, hwnd)
        del _filter_specs
        if hr == _E_CANCELLED:
            return None
        _check(hr)

        if allow_multiple:
            item_array = ctypes.c_void_p()
            _check(
                _com_fn(dialog, _VTBL_GET_RESULTS, _HRESULT, ctypes.POINTER(ctypes.c_void_p))(
                    dialog, ctypes.byref(item_array)
                )
            )
            try:
                count = ctypes.c_uint32()
                _check(
                    _com_fn(
                        item_array, _VTBL_SA_GET_COUNT, _HRESULT, ctypes.POINTER(ctypes.c_uint32)
                    )(item_array, ctypes.byref(count))
                )

                paths: list[str] = []
                for i in range(count.value):
                    item = ctypes.c_void_p()
                    hr = _com_fn(
                        item_array,
                        _VTBL_SA_GET_ITEM,
                        _HRESULT,
                        ctypes.c_uint32,
                        ctypes.POINTER(ctypes.c_void_p),
                    )(item_array, i, ctypes.byref(item))
                    if hr:
                        _log.warning('IShellItemArray::GetItemAt(%d) failed: 0x%08x', i, hr)
                        continue
                    try:
                        path = _shell_item_path(item)
                        if path is not None:
                            paths.append(path)
                    finally:
                        _com_release(item)

                return paths
            finally:
                _com_release(item_array)
        else:
            item = ctypes.c_void_p()
            _check(
                _com_fn(dialog, _VTBL_GET_RESULT, _HRESULT, ctypes.POINTER(ctypes.c_void_p))(
                    dialog, ctypes.byref(item)
                )
            )
            try:
                path = _shell_item_path(item)
                return [path] if path is not None else None
            finally:
                _com_release(item)
    finally:
        _com_release(dialog)


def pick_save_file_win32(
    hwnd: int,
    suggested_file_name: str,
    file_types: list[str],
    directory: str | None = None,
) -> str | None:
    """
    Show a save-file dialog via IFileSaveDialog (Win32 COM), honoring an initial
    directory that the WinRT FileSavePicker cannot express.

    Must be called on a COM-initialised (STA) thread.
    Returns the selected file path, or None if the user cancelled.
    """
    dialog = ctypes.c_void_p()
    _check(
        _ole32.CoCreateInstance(
            ctypes.byref(_CLSID_FileSaveDialog),
            None,
            _CLSCTX_INPROC_SERVER,
            ctypes.byref(_IID_IFileDialog),
            ctypes.byref(dialog),
        )
    )

    try:
        # kept alive until Show() returns: SetFileTypes reads these strings by pointer
        _filter_specs = _set_dialog_file_types(dialog, file_types) if file_types else None

        if suggested_file_name:
            _check(
                _com_fn(dialog, _VTBL_SET_FILE_NAME, _HRESULT, wintypes.LPCWSTR)(
                    dialog, suggested_file_name
                )
            )

        if directory:
            _set_dialog_folder(dialog, directory)

        hr = _com_fn(dialog, _VTBL_SHOW, _HRESULT, wintypes.HWND)(dialog, hwnd)
        del _filter_specs
        if hr == _E_CANCELLED:
            return None
        _check(hr)

        item = ctypes.c_void_p()
        _check(
            _com_fn(dialog, _VTBL_GET_RESULT, _HRESULT, ctypes.POINTER(ctypes.c_void_p))(
                dialog, ctypes.byref(item)
            )
        )
        try:
            return _shell_item_path(item)
        finally:
            _com_release(item)
    finally:
        _com_release(dialog)
