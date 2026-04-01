import ctypes
import logging as _logging
import sys
from contextlib import ExitStack
from ctypes import WinError, byref, wintypes
from typing import Optional

from win32more import FAILED, Guid
from win32more.Windows.Win32.Foundation import (
    ERROR_CANCELLED,
    PWSTR,
)
from win32more.Windows.Win32.System.Com import (
    CLSCTX_ALL,
    CoCreateInstance,
    CoTaskMemFree,
)
from win32more.Windows.Win32.System.LibraryLoader import GetModuleHandle
from win32more.Windows.Win32.UI.Shell import (
    SIGDN_FILESYSPATH,
    ExtractIcon,
    FileSaveDialog,
    FOLDERID_Downloads,
    FOLDERID_RoamingAppData,
    IFileSaveDialog,
    IShellItem,
    SHGetKnownFolderItem,
    SHGetKnownFolderPath,
)
from win32more.Windows.Win32.UI.Shell.Common import COMDLG_FILTERSPEC
from win32more.Windows.Win32.UI.WindowsAndMessaging import (
    GWL_EXSTYLE,
    WS_EX_NOACTIVATE,
    GetWindowLong,
    SetWindowLong,
)

_log = _logging.getLogger('pywebview')

_WM_MOUSEWHEEL = 0x020A
_WM_MOUSEHWHEEL = 0x020E
_WH_MOUSE_LL = 14


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

_LowLevelMouseProcType = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, ctypes.c_void_p
)
_EnumChildProcType = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


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


def install_mouse_wheel_hook(hwnd: int):
    """
    Install a WH_MOUSE_LL (low-level mouse) hook that intercepts WM_MOUSEWHEEL
    and WM_MOUSEHWHEEL system-wide and forwards them to the WebView2 input
    HWND (or, if compositor hosting is used and no Chrome HWND exists, to the
    window directly under the cursor).  WH_MOUSE_LL fires on the installing
    thread for all mouse input regardless of which thread owns the target window.

    Returns (hook_proc, hook_handle); the caller must keep references to both
    to prevent GC.
    """
    hook_handle: list = [None]
    # Use a list with a sentinel so we distinguish "not yet searched" (None)
    # from "searched and not found" (0).
    input_hwnd_cache: list = [None]

    def _get_input_hwnd() -> int | None:
        if input_hwnd_cache[0] is None:
            found = _find_input_hwnd(hwnd)
            input_hwnd_cache[0] = found if found else 0
        return input_hwnd_cache[0] or None

    @_LowLevelMouseProcType
    def hook_proc(nCode, wParam, lParam):
        if nCode >= 0 and lParam and wParam in (_WM_MOUSEWHEEL, _WM_MOUSEHWHEEL):
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
        _log.error('Failed to install mouse wheel hook for hwnd=0x%x', hwnd)
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
def HRESULT_CODE(x):
    return x & 0xFFFF


def get_known_folder_path(folder_id: Guid) -> str:
    _folder = PWSTR()
    hr = SHGetKnownFolderPath(folder_id, 0, None, byref(_folder))
    if FAILED(hr):
        raise WinError(hr)

    folder = _folder.value
    CoTaskMemFree(_folder)
    return folder


def get_roaming_app_data_path() -> str:
    return get_known_folder_path(FOLDERID_RoamingAppData)


def get_app_icon_handle() -> int:
    module = GetModuleHandle(None)
    if not module:
        raise WinError()

    icon = ExtractIcon(module, sys.executable, 0)
    if not icon:
        raise WinError()

    return icon


def set_window_noactivate(hwnd: int) -> None:
    flags = GetWindowLong(hwnd, GWL_EXSTYLE)
    if not flags:
        raise WinError()

    flags = SetWindowLong(hwnd, GWL_EXSTYLE, flags | WS_EX_NOACTIVATE)
    if not flags:
        raise WinError()


def show_save_file_dialog(
    parent_hwnd: int, file_name: str, file_type: str, file_spec: str
) -> Optional[str]:
    with ExitStack() as stack:
        dialog = IFileSaveDialog()
        hr = CoCreateInstance(FileSaveDialog, None, CLSCTX_ALL, IFileSaveDialog._iid_, dialog)
        if FAILED(hr):
            raise WinError(hr)
        stack.callback(dialog.Release)

        folder = IShellItem()
        hr = SHGetKnownFolderItem(FOLDERID_Downloads, 0, None, IShellItem._iid_, folder)
        if FAILED(hr):
            raise WinError(hr)
        stack.callback(folder.Release)

        hr = dialog.SetDefaultFolder(folder)
        if FAILED(hr):
            raise WinError(hr)

        types = COMDLG_FILTERSPEC()
        types.pszName = file_type
        types.pszSpec = file_spec
        hr = dialog.SetFileTypes(1, byref(types))
        if FAILED(hr):
            raise WinError(hr)

        hr = dialog.SetFileName(file_name)
        if FAILED(hr):
            raise WinError(hr)

        hr = dialog.Show(parent_hwnd)
        if HRESULT_CODE(hr) == ERROR_CANCELLED:
            return None
        if FAILED(hr):
            raise WinError(hr)

        item = IShellItem()
        hr = dialog.GetResult(item)
        if FAILED(hr):
            raise WinError(hr)
        stack.callback(item.Release)

        path = PWSTR()
        hr = item.GetDisplayName(SIGDN_FILESYSPATH, path)
        if FAILED(hr):
            raise WinError(hr)
        stack.callback(CoTaskMemFree, path)

        return path.value
