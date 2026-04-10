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
_user32.GetWindowRect.restype = wintypes.BOOL
_user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
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
    # Drag state: [phase, cursor_start_x, cursor_start_y, win_start_x, win_start_y]
    # phase: 0=inactive, 1=pending (waiting for first WM_MOUSEMOVE), 2=active
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
                    hs = ctypes.cast(
                        ctypes.c_void_p(lParam), ctypes.POINTER(_MSLLHOOKSTRUCT)
                    ).contents
                    if _drag[0] == 1:
                        # Pending → active: record start cursor from the hook
                        # struct so coordinates are in the same physical space.
                        _drag[0] = 2
                        _drag[1] = hs.pt_x
                        _drag[2] = hs.pt_y
                    else:
                        _user32.SetWindowPos(
                            hwnd,
                            0,
                            _drag[3] + hs.pt_x - _drag[1],
                            _drag[4] + hs.pt_y - _drag[2],
                            0,
                            0,
                            _SWP_NOSIZE | _SWP_NOZORDER | _SWP_NOACTIVATE,
                        )
                    return 1  # suppress so Chrome doesn't also handle the move

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


def start_drag(hwnd: int) -> None:
    """Initiate a native window drag (title-bar grab) via Win32.

    For hwnds with a mouse hook installed (WinUI3), the drag is handled
    inside the hook using SetWindowPos.  For other hwnds (WinForms), the
    standard ReleaseCapture / WM_NCLBUTTONDOWN approach is used.
    """
    drag = _drag_states.get(hwnd)
    if drag is not None:
        rect = wintypes.RECT()
        _user32.GetWindowRect(hwnd, ctypes.byref(rect))
        drag[0] = 1  # pending — hook captures start cursor on first WM_MOUSEMOVE
        drag[3] = rect.left
        drag[4] = rect.top
    else:
        _user32.ReleaseCapture()
        _user32.SendMessageW(hwnd, _WM_NCLBUTTONDOWN, _HT_CAPTION, 0)
