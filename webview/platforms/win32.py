import ctypes
import logging as _logging
import sys
from contextlib import ExitStack
from ctypes import WinError, byref
from ctypes import wintypes
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
    FileOpenDialog,
    FileSaveDialog,
    FOLDERID_Downloads,
    FOLDERID_RoamingAppData,
    IFileOpenDialog,
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


def show_open_file_dialog():
    with ExitStack() as stack:
        dialog = IFileOpenDialog()
        hr = CoCreateInstance(
            FileOpenDialog, None, CLSCTX_ALL, IFileOpenDialog._iid_, dialog
        )
        if FAILED(hr):
            raise WinError(hr)
        stack.callback(dialog.Release)

        hr = dialog.Show(0)
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


def show_save_file_dialog(
    parent_hwnd: int, file_name: str, file_type: str, file_spec: str
) -> Optional[str]:
    with ExitStack() as stack:
        dialog = IFileSaveDialog()
        hr = CoCreateInstance(
            FileSaveDialog, None, CLSCTX_ALL, IFileSaveDialog._iid_, dialog
        )
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
