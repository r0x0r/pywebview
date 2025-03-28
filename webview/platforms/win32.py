import sys
from contextlib import ExitStack
from ctypes import WinError, byref
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
