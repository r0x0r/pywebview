import ctypes
import logging as _logging
from ctypes import wintypes

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
_user32.PhysicalToLogicalPointForPerMonitorDPI.restype = wintypes.BOOL
_user32.PhysicalToLogicalPointForPerMonitorDPI.argtypes = [
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
_user32.MonitorFromRect.restype = wintypes.HANDLE
_user32.MonitorFromRect.argtypes = [ctypes.POINTER(wintypes.RECT), wintypes.DWORD]
_user32.GetMonitorInfoW.restype = wintypes.BOOL
_user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
_user32.EnumDisplaySettingsW.restype = wintypes.BOOL
_user32.EnumDisplaySettingsW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p]

_LowLevelMouseProcType = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, ctypes.c_void_p
)
_EnumChildProcType = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

# hwnd → drag state list registered by install_mouse_hook.
# start_drag() uses this to choose the hook-based path for WinUI3.
_drag_states: dict[int, list] = {}


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
    # Drag state: [active, cursor_start_x, cursor_start_y, win_start_x, win_start_y]
    # active: 0=inactive, 1=dragging
    _drag: list = [0, 0, 0, 0, 0]
    _drag_states[hwnd] = _drag

    def _get_input_hwnd() -> int | None:
        if input_hwnd_cache[0] is None:
            found = _find_input_hwnd(hwnd)
            input_hwnd_cache[0] = found if found else 0
        return input_hwnd_cache[0] or None

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
                    _user32.PhysicalToLogicalPointForPerMonitorDPI(hwnd, ctypes.byref(pt))
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
                    # Prefer the dedicated Chrome input HWND; fall back to the
                    # window directly under the cursor (compositor hosting case).
                    target = _get_input_hwnd() or window_at_cursor
                    lparam = ((logical_pt.y & 0xFFFF) << 16) | (logical_pt.x & 0xFFFF)
                    _user32.PostMessageW(target, wParam, hs.mouseData, lparam)
                    return 1  # suppress original so XAML doesn't swallow it

        return _user32.CallNextHookEx(hook_handle[0], nCode, wParam, lParam)

    # WH_MOUSE_LL is a global hook — pass thread_id=0, no DLL required.
    hook_handle[0] = _user32.SetWindowsHookExW(_WH_MOUSE_LL, hook_proc, None, 0)
    if not hook_handle[0]:
        _log.error('Failed to install mouse hook for hwnd=0x%x', hwnd)
    return hook_proc, hook_handle[0]


_user32 = ctypes.windll.user32


# DEVMODE structure for EnumDisplaySettings
class DEVMODE(ctypes.Structure):
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


# DISPLAY_DEVICEW structure for EnumDisplayDevices
class DISPLAY_DEVICEW(ctypes.Structure):
    _fields_ = [
        ('cb', wintypes.DWORD),
        ('DeviceName', wintypes.WCHAR * 32),
        ('DeviceString', wintypes.WCHAR * 128),
        ('StateFlags', wintypes.DWORD),
        ('DeviceID', wintypes.WCHAR * 128),
        ('DeviceKey', wintypes.WCHAR * 128),
    ]


def get_screen_scale(device_name: str, logical_width: int, logical_height: int) -> float:
    """
    Calculate the DPI scale factor for a screen.

    Args:
        device_name: The device name (e.g., "\\\\.\\DISPLAY1")
        logical_width: The logical width in pixels (DPI-scaled)
        logical_height: The logical height in pixels (DPI-scaled)

    Returns:
        The scale factor (e.g., 1.0, 1.5, 2.0, etc.)
    """
    try:
        dm = DEVMODE()
        dm.dmSize = ctypes.sizeof(DEVMODE)

        # ENUM_CURRENT_SETTINGS = -1
        if _user32.EnumDisplaySettingsW(device_name, -1, ctypes.byref(dm)):
            physical_width = dm.dmPelsWidth
        else:
            # Fallback to logical size if EnumDisplaySettings fails
            return 1.0

        # Calculate scale from the ratio
        if logical_width > 0 and logical_height > 0:
            return physical_width / logical_width
        else:
            return 1.0

    except Exception as e:
        _log.debug(f'Failed to get display settings: {e}')
        return 1.0


def start_drag(hwnd: int) -> None:
    """Initiate a native window drag (title-bar grab) via Win32.

    For hwnds with a mouse hook installed (WinUI3), the drag is handled
    inside the hook using SetWindowPos. For other hwnds (WinForms), the
    standard ReleaseCapture / WM_NCLBUTTONDOWN approach is used.
    """
    if _user32.IsZoomed(hwnd):
        return

    # Only start drag if left mouse button is pressed
    if not (_user32.GetKeyState(_VK_LBUTTON) & 0x8000):
        return

    drag = _drag_states.get(hwnd)
    if drag is not None:
        rect = wintypes.RECT()
        _user32.GetWindowRect(hwnd, ctypes.byref(rect))
        cursor = wintypes.POINT()
        _user32.GetCursorPos(ctypes.byref(cursor))
        drag[0] = 1
        drag[1] = cursor.x
        drag[2] = cursor.y
        drag[3] = rect.left
        drag[4] = rect.top
    else:
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

    Two independent methods are tried because the correct one depends on the
    calling thread's DPI-awareness context:

    * **System-DPI-aware** (WinForms): ``GetDpiForMonitor`` returns 96
      regardless of actual scaling, but ``rcMonitor`` from
      ``GetMonitorInfoW`` is in logical pixels so the physical/logical ratio
      gives the correct scale.
    * **Per-monitor-DPI-aware** (WinUI3 / WinRT threads): ``rcMonitor`` is
      in physical pixels (ratio = 1.0) but ``GetDpiForMonitor`` returns the
      real DPI.

    Taking the ``max`` of both results picks whichever method detected
    scaling.

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

        return max(scale_from_dpi, scale_from_ratio)

    except Exception as e:
        _log.debug(f'Failed to get monitor scale: {e}')

    return 1.0
