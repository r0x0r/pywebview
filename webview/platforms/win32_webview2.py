"""
WebView2 hosted in a plain Win32 window, driven through PyWinRT.

Unlike the WinUI 3 backend, this one needs no Windows App Runtime: the window
is an ordinary top-level HWND, and WebView2 is attached to it with
CoreWebView2Controller. Everything the Windows Runtime offers is used through
PyWinRT - WebView2 itself, the UI-thread DispatcherQueue, MessageDialog, the
file pickers and ApplicationData. Only what has no WinRT API for an unpackaged
desktop process - creating the window, its message loop, its menu bar and
enumerating monitors - is done with ctypes.
"""

import atexit
import contextlib
import ctypes
import json
import logging
import os
import sys
import tempfile
import threading
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import Future, wait
from ctypes import WinError, wintypes
from datetime import datetime, timezone
from email.utils import format_datetime
from http.cookies import SimpleCookie
from threading import Event, Lock, Semaphore
from typing import cast

from winrt.microsoft.web.webview2.core import (
    CoreWebView2,
    CoreWebView2CompositionController,
    CoreWebView2Controller,
    CoreWebView2ControllerWindowReference,
    CoreWebView2Cookie,
    CoreWebView2CookieSameSiteKind,
    CoreWebView2DownloadStartingEventArgs,
    CoreWebView2Environment,
    CoreWebView2EnvironmentOptions,
    CoreWebView2File,
    CoreWebView2MouseEventKind,
    CoreWebView2MouseEventVirtualKeys,
    CoreWebView2MoveFocusReason,
    CoreWebView2NavigationCompletedEventArgs,
    CoreWebView2NewWindowRequestedEventArgs,
    CoreWebView2PointerEventKind,
    CoreWebView2ProcessFailedEventArgs,
    CoreWebView2ProcessFailedKind,
    CoreWebView2ServerCertificateErrorAction,
    CoreWebView2ServerCertificateErrorDetectedEventArgs,
    CoreWebView2SourceChangedEventArgs,
    CoreWebView2WebMessageReceivedEventArgs,
    CoreWebView2WebResourceContext,
    CoreWebView2WebResourceRequestedEventArgs,
    CoreWebView2WebResourceResponseReceivedEventArgs,
)
from winrt.microsoft.web.webview2.interop import DropTarget, register_drop_target
from winrt.runtime import ApartmentType, init_apartment, uninit_apartment
from winrt.runtime.interop import initialize_with_window
from winrt.windows.devices.input import PointerDeviceType
from winrt.windows.foundation import AsyncStatus, IAsyncAction, IAsyncOperation, Rect
from winrt.windows.storage import ApplicationData, StorageFile, StorageFolder
from winrt.windows.storage.pickers import (
    FileOpenPicker,
    FileSavePicker,
    FolderPicker,
    PickerLocationId,
)
from winrt.windows.system import DispatcherQueue, DispatcherQueueController
from winrt.windows.system.interop import (
    DispatcherQueueThreadApartmentType,
    DispatcherQueueThreadType,
    create_dispatcher_queue_controller,
)
from winrt.windows.ui import Color
from winrt.windows.ui.composition import Compositor
from winrt.windows.ui.composition.desktop import DesktopWindowTarget
from winrt.windows.ui.composition.interop import create_desktop_window_target
from winrt.windows.ui.core import CoreCursorType
from winrt.windows.ui.input import PointerPoint
from winrt.windows.ui.popups import IUICommand, MessageDialog, UICommand

from webview import FileDialog, _state, windows
from webview import settings as webview_settings
from webview.menu import Menu, MenuAction, MenuSeparator
from webview.platforms.webview2core import WebView2Core
from webview.platforms.win32 import (
    enable_window_shadow,
    pick_files_win32,
    pick_folders_win32,
    pick_save_file_win32,
)
from webview.screen import Screen
from webview.util import (
    create_cookie,
    get_app_root,
    inject_base_uri,
    inject_pywebview,
    parse_file_type,
)
from webview.window import FixPoint
from webview.window import Window as _Window

logger = logging.getLogger('pywebview')
cache_dir: str | None = None

# The page sees the same WebView2 as the WinForms backend's, so the injected
# JavaScript takes the same 'edgechromium' path (chrome.webview.postMessage).
renderer = 'edgechromium'

logger.debug('Using Win32 / Chromium (WebView2 through PyWinRT)')


# ── Win32 declarations ───────────────────────────────────────────────────────

_user32 = ctypes.WinDLL('user32', use_last_error=True)
_kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
_gdi32 = ctypes.WinDLL('gdi32', use_last_error=True)
_shcore = ctypes.WinDLL('shcore', use_last_error=True)
_shell32 = ctypes.WinDLL('shell32', use_last_error=True)

_LRESULT = ctypes.c_ssize_t
_WNDPROC = ctypes.WINFUNCTYPE(
    _LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
)
_MONITORENUMPROC = ctypes.WINFUNCTYPE(
    wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM
)


class _WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.UINT),
        ('style', wintypes.UINT),
        ('lpfnWndProc', _WNDPROC),
        ('cbClsExtra', ctypes.c_int),
        ('cbWndExtra', ctypes.c_int),
        ('hInstance', wintypes.HINSTANCE),
        ('hIcon', wintypes.HICON),
        ('hCursor', wintypes.HANDLE),
        ('hbrBackground', wintypes.HBRUSH),
        ('lpszMenuName', wintypes.LPCWSTR),
        ('lpszClassName', wintypes.LPCWSTR),
        ('hIconSm', wintypes.HICON),
    ]


class _MINMAXINFO(ctypes.Structure):
    _fields_ = [
        ('ptReserved', wintypes.POINT),
        ('ptMaxSize', wintypes.POINT),
        ('ptMaxPosition', wintypes.POINT),
        ('ptMinTrackSize', wintypes.POINT),
        ('ptMaxTrackSize', wintypes.POINT),
    ]


class _MONITORINFO(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.DWORD),
        ('rcMonitor', wintypes.RECT),
        ('rcWork', wintypes.RECT),
        ('dwFlags', wintypes.DWORD),
    ]


class _WINDOWPLACEMENT(ctypes.Structure):
    _fields_ = [
        ('length', wintypes.UINT),
        ('flags', wintypes.UINT),
        ('showCmd', wintypes.UINT),
        ('ptMinPosition', wintypes.POINT),
        ('ptMaxPosition', wintypes.POINT),
        ('rcNormalPosition', wintypes.RECT),
    ]


def _declare(dll, name: str, restype, *argtypes):
    function = getattr(dll, name)
    function.restype = restype
    function.argtypes = list(argtypes)
    return function


_HWND = wintypes.HWND
_UINT = wintypes.UINT
_INT = ctypes.c_int
_BOOL = wintypes.BOOL

_RegisterClassExW = _declare(
    _user32, 'RegisterClassExW', wintypes.ATOM, ctypes.POINTER(_WNDCLASSEXW)
)
_CreateWindowExW = _declare(
    _user32,
    'CreateWindowExW',
    _HWND,
    wintypes.DWORD,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    _INT,
    _INT,
    _INT,
    _INT,
    _HWND,
    wintypes.HMENU,
    wintypes.HINSTANCE,
    wintypes.LPVOID,
)
_DefWindowProcW = _declare(
    _user32, 'DefWindowProcW', _LRESULT, _HWND, _UINT, wintypes.WPARAM, wintypes.LPARAM
)
_DestroyWindow = _declare(_user32, 'DestroyWindow', _BOOL, _HWND)
_ShowWindow = _declare(_user32, 'ShowWindow', _BOOL, _HWND, _INT)
_IsWindowVisible = _declare(_user32, 'IsWindowVisible', _BOOL, _HWND)
_IsIconic = _declare(_user32, 'IsIconic', _BOOL, _HWND)
_SetForegroundWindow = _declare(_user32, 'SetForegroundWindow', _BOOL, _HWND)
_GetFocus = _declare(_user32, 'GetFocus', _HWND)
_SetWindowTextW = _declare(_user32, 'SetWindowTextW', _BOOL, _HWND, wintypes.LPCWSTR)
_GetWindowRect = _declare(_user32, 'GetWindowRect', _BOOL, _HWND, ctypes.POINTER(wintypes.RECT))
_GetClientRect = _declare(_user32, 'GetClientRect', _BOOL, _HWND, ctypes.POINTER(wintypes.RECT))
_SetWindowPos = _declare(
    _user32, 'SetWindowPos', _BOOL, _HWND, _HWND, _INT, _INT, _INT, _INT, _UINT
)
# 32-bit user32 exports these only under their 32-bit names; the Ptr names are macros there.
_LONG_PTR_SUFFIX = 'LongPtrW' if ctypes.sizeof(ctypes.c_void_p) == 8 else 'LongW'
_GetWindowLongPtrW = _declare(
    _user32, f'GetWindow{_LONG_PTR_SUFFIX}', ctypes.c_ssize_t, _HWND, _INT
)
_SetWindowLongPtrW = _declare(
    _user32, f'SetWindow{_LONG_PTR_SUFFIX}', ctypes.c_ssize_t, _HWND, _INT, ctypes.c_ssize_t
)
_GetWindowPlacement = _declare(
    _user32, 'GetWindowPlacement', _BOOL, _HWND, ctypes.POINTER(_WINDOWPLACEMENT)
)
_SetWindowPlacement = _declare(
    _user32, 'SetWindowPlacement', _BOOL, _HWND, ctypes.POINTER(_WINDOWPLACEMENT)
)
_GetDpiForWindow = _declare(_user32, 'GetDpiForWindow', _UINT, _HWND)
_SendMessageW = _declare(
    _user32, 'SendMessageW', _LRESULT, _HWND, _UINT, wintypes.WPARAM, wintypes.LPARAM
)
_GetMessageW = _declare(
    _user32, 'GetMessageW', _BOOL, ctypes.POINTER(wintypes.MSG), _HWND, _UINT, _UINT
)
_TranslateMessage = _declare(_user32, 'TranslateMessage', _BOOL, ctypes.POINTER(wintypes.MSG))
_DispatchMessageW = _declare(_user32, 'DispatchMessageW', _LRESULT, ctypes.POINTER(wintypes.MSG))
_PostQuitMessage = _declare(_user32, 'PostQuitMessage', None, _INT)
_PeekMessageW = _declare(
    _user32, 'PeekMessageW', _BOOL, ctypes.POINTER(wintypes.MSG), _HWND, _UINT, _UINT, _UINT
)
_HANDLER_ROUTINE = ctypes.WINFUNCTYPE(_BOOL, wintypes.DWORD)
_SetConsoleCtrlHandler = _declare(
    _kernel32, 'SetConsoleCtrlHandler', _BOOL, _HANDLER_ROUTINE, _BOOL
)
_CTRL_C_EVENT = 0
_PostThreadMessageW = _declare(
    _user32, 'PostThreadMessageW', _BOOL, wintypes.DWORD, _UINT, wintypes.WPARAM, wintypes.LPARAM
)
_LoadCursorW = _declare(
    _user32, 'LoadCursorW', wintypes.HANDLE, wintypes.HINSTANCE, wintypes.LPVOID
)
_LoadImageW = _declare(
    _user32,
    'LoadImageW',
    wintypes.HANDLE,
    wintypes.HINSTANCE,
    wintypes.LPCWSTR,
    _UINT,
    _INT,
    _INT,
    _UINT,
)
_CreateIconFromResourceEx = _declare(
    _user32,
    'CreateIconFromResourceEx',
    wintypes.HICON,
    ctypes.c_char_p,
    wintypes.DWORD,
    _BOOL,
    wintypes.DWORD,
    _INT,
    _INT,
    _UINT,
)
_DestroyIcon = _declare(_user32, 'DestroyIcon', _BOOL, wintypes.HICON)
_GetSystemMetrics = _declare(_user32, 'GetSystemMetrics', _INT, _INT)
_CreateMenu = _declare(_user32, 'CreateMenu', wintypes.HMENU)
_CreatePopupMenu = _declare(_user32, 'CreatePopupMenu', wintypes.HMENU)
_AppendMenuW = _declare(
    _user32, 'AppendMenuW', _BOOL, wintypes.HMENU, _UINT, ctypes.c_size_t, wintypes.LPCWSTR
)
_GetMenu = _declare(_user32, 'GetMenu', wintypes.HMENU, _HWND)
_SetMenu = _declare(_user32, 'SetMenu', _BOOL, _HWND, wintypes.HMENU)
_SetCursor = _declare(_user32, 'SetCursor', wintypes.HANDLE, wintypes.HANDLE)
_SetCapture = _declare(_user32, 'SetCapture', _HWND, _HWND)
_ReleaseCapture = _declare(_user32, 'ReleaseCapture', _BOOL)
_GetCapture = _declare(_user32, 'GetCapture', _HWND)
_ScreenToClient = _declare(_user32, 'ScreenToClient', _BOOL, _HWND, ctypes.POINTER(wintypes.POINT))


class _TRACKMOUSEEVENT(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.DWORD),
        ('dwFlags', wintypes.DWORD),
        ('hwndTrack', _HWND),
        ('dwHoverTime', wintypes.DWORD),
    ]


_TrackMouseEvent = _declare(_user32, 'TrackMouseEvent', _BOOL, ctypes.POINTER(_TRACKMOUSEEVENT))
_DestroyMenu = _declare(_user32, 'DestroyMenu', _BOOL, wintypes.HMENU)
_DrawMenuBar = _declare(_user32, 'DrawMenuBar', _BOOL, _HWND)
_FillRect = _declare(
    _user32, 'FillRect', _INT, wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.HBRUSH
)
_GetAncestor = _declare(_user32, 'GetAncestor', _HWND, _HWND, wintypes.UINT)
_GetCursorPos = _declare(_user32, 'GetCursorPos', _BOOL, ctypes.POINTER(wintypes.POINT))
_GetMessageTime = _declare(_user32, 'GetMessageTime', wintypes.LONG)
_WindowFromPoint = _declare(_user32, 'WindowFromPoint', _HWND, wintypes.POINT)
_MonitorFromPoint = _declare(
    _user32, 'MonitorFromPoint', wintypes.HMONITOR, wintypes.POINT, wintypes.DWORD
)
_MonitorFromWindow = _declare(
    _user32, 'MonitorFromWindow', wintypes.HMONITOR, _HWND, wintypes.DWORD
)
_GetMonitorInfoW = _declare(
    _user32, 'GetMonitorInfoW', _BOOL, wintypes.HMONITOR, ctypes.POINTER(_MONITORINFO)
)
_EnumDisplayMonitors = _declare(
    _user32,
    'EnumDisplayMonitors',
    _BOOL,
    wintypes.HDC,
    ctypes.POINTER(wintypes.RECT),
    _MONITORENUMPROC,
    wintypes.LPARAM,
)
_GetModuleHandleW = _declare(_kernel32, 'GetModuleHandleW', wintypes.HMODULE, wintypes.LPCWSTR)
_GetCurrentThreadId = _declare(_kernel32, 'GetCurrentThreadId', wintypes.DWORD)
_CreateSolidBrush = _declare(_gdi32, 'CreateSolidBrush', wintypes.HBRUSH, wintypes.COLORREF)
_DeleteObject = _declare(_gdi32, 'DeleteObject', _BOOL, wintypes.HGDIOBJ)
_GetDpiForMonitor = _declare(
    _shcore,
    'GetDpiForMonitor',
    ctypes.c_long,
    wintypes.HMONITOR,
    _INT,
    ctypes.POINTER(_UINT),
    ctypes.POINTER(_UINT),
)
_IsUserAnAdmin = _declare(_shell32, 'IsUserAnAdmin', _BOOL)
_ExtractIconExW = _declare(
    _shell32,
    'ExtractIconExW',
    _UINT,
    wintypes.LPCWSTR,
    _INT,
    ctypes.POINTER(wintypes.HICON),
    ctypes.POINTER(wintypes.HICON),
    _UINT,
)

_WM_NULL = 0x0000
_WM_DESTROY = 0x0002
_WM_MOVE = 0x0003
_WM_SIZE = 0x0005
_WM_ACTIVATE = 0x0006
_WM_SETFOCUS = 0x0007
_WM_CLOSE = 0x0010
_WM_ERASEBKGND = 0x0014
_WM_GETMINMAXINFO = 0x0024
_WM_SETICON = 0x0080
_WM_NCDESTROY = 0x0082
_WM_COMMAND = 0x0111
_WM_DPICHANGED = 0x02E0
_WM_ENDSESSION = 0x0016
_WM_QUIT = 0x0012
_PM_REMOVE = 0x0001

_WA_INACTIVE = 0
_SIZE_RESTORED = 0
_SIZE_MINIMIZED = 1
_SIZE_MAXIMIZED = 2

_WS_POPUP = 0x80000000
_WS_CAPTION = 0x00C00000
_WS_SYSMENU = 0x00080000
_WS_THICKFRAME = 0x00040000
_WS_MINIMIZEBOX = 0x00020000
_WS_MAXIMIZEBOX = 0x00010000
_WS_OVERLAPPEDWINDOW = (
    _WS_CAPTION | _WS_SYSMENU | _WS_THICKFRAME | _WS_MINIMIZEBOX | _WS_MAXIMIZEBOX
)
_WS_EX_TOPMOST = 0x00000008
_WS_EX_NOACTIVATE = 0x08000000
_WS_EX_APPWINDOW = 0x00040000
_WS_EX_NOREDIRECTIONBITMAP = 0x00200000

_WM_NCHITTEST = 0x0084
_WM_SETCURSOR = 0x0020
_WM_MOUSEMOVE = 0x0200
_WM_LBUTTONDOWN = 0x0201
_WM_LBUTTONUP = 0x0202
_WM_LBUTTONDBLCLK = 0x0203
_WM_RBUTTONDOWN = 0x0204
_WM_RBUTTONUP = 0x0205
_WM_RBUTTONDBLCLK = 0x0206
_WM_MBUTTONDOWN = 0x0207
_WM_MBUTTONUP = 0x0208
_WM_MBUTTONDBLCLK = 0x0209
_WM_MOUSEWHEEL = 0x020A
_WM_XBUTTONDOWN = 0x020B
_WM_XBUTTONUP = 0x020C
_WM_XBUTTONDBLCLK = 0x020D
_WM_MOUSEHWHEEL = 0x020E
_WM_CAPTURECHANGED = 0x0215
_WM_MOUSELEAVE = 0x02A3
_HTCLIENT = 1
_TME_LEAVE = 0x00000002
_MK_BUTTONS = 0x0001 | 0x0002 | 0x0010 | 0x0020 | 0x0040
_GA_ROOT = 2
# The mouse messages a visually hosted WebView2 is sent, each as the
# CoreWebView2MouseEventKind of the same value.
_FORWARDED_MOUSE_MESSAGES = frozenset(
    {
        _WM_MOUSEMOVE,
        _WM_LBUTTONDOWN,
        _WM_LBUTTONUP,
        _WM_LBUTTONDBLCLK,
        _WM_RBUTTONDOWN,
        _WM_RBUTTONUP,
        _WM_RBUTTONDBLCLK,
        _WM_MBUTTONDOWN,
        _WM_MBUTTONUP,
        _WM_MBUTTONDBLCLK,
        _WM_MOUSEWHEEL,
        _WM_XBUTTONDOWN,
        _WM_XBUTTONUP,
        _WM_XBUTTONDBLCLK,
        _WM_MOUSEHWHEEL,
        _WM_MOUSELEAVE,
    }
)
# Where WebView2 is sent the release of a press whose capture was taken
# away: outside the page, as for a press dragged out of it, so that the
# page sees the release but no element is clicked.
_RELEASE_OUTSIDE_POINT = (-32000, -32000)
# For each press (a double click's second press is one too), the release
# that ends it.
_BUTTON_RELEASES = {
    _WM_LBUTTONDOWN: CoreWebView2MouseEventKind.LEFT_BUTTON_UP,
    _WM_LBUTTONDBLCLK: CoreWebView2MouseEventKind.LEFT_BUTTON_UP,
    _WM_RBUTTONDOWN: CoreWebView2MouseEventKind.RIGHT_BUTTON_UP,
    _WM_RBUTTONDBLCLK: CoreWebView2MouseEventKind.RIGHT_BUTTON_UP,
    _WM_MBUTTONDOWN: CoreWebView2MouseEventKind.MIDDLE_BUTTON_UP,
    _WM_MBUTTONDBLCLK: CoreWebView2MouseEventKind.MIDDLE_BUTTON_UP,
    _WM_XBUTTONDOWN: CoreWebView2MouseEventKind.X_BUTTON_UP,
    _WM_XBUTTONDBLCLK: CoreWebView2MouseEventKind.X_BUTTON_UP,
}
_BUTTON_UP_MESSAGES = frozenset({_WM_LBUTTONUP, _WM_RBUTTONUP, _WM_MBUTTONUP, _WM_XBUTTONUP})
_X_BUTTON_MESSAGES = frozenset({_WM_XBUTTONDOWN, _WM_XBUTTONUP, _WM_XBUTTONDBLCLK})

_WM_POINTERUPDATE = 0x0245
_WM_POINTERDOWN = 0x0246
_WM_POINTERUP = 0x0247
_WM_POINTERENTER = 0x0249
_WM_POINTERLEAVE = 0x024A
# The touch and pen messages a visually hosted WebView2 is sent, each as the
# CoreWebView2PointerEventKind of the same value. Not WM_POINTERACTIVATE,
# whose lparam is a window, not a point: activating the window is the
# default's to do.
_FORWARDED_POINTER_MESSAGES = frozenset(
    {_WM_POINTERUPDATE, _WM_POINTERDOWN, _WM_POINTERUP, _WM_POINTERENTER, _WM_POINTERLEAVE}
)
# The POINTER_FLAG_DOWN or _UP that a message stands for, or else _UPDATE;
# the message's other flags are the high word of its wparam.
_POINTER_EVENT_FLAGS = {
    _WM_POINTERDOWN: 0x00010000,
    _WM_POINTERUP: 0x00040000,
}
_POINTER_FLAG_UPDATE = 0x00020000
_PT_TOUCH = 2
_PT_PEN = 3
_TOUCH_MASK_ALL = 0x7  # TOUCH_MASK_CONTACTAREA | _ORIENTATION | _PRESSURE
_PEN_MASK_ALL = 0xF  # PEN_MASK_PRESSURE | _ROTATION | _TILT_X | _TILT_Y
_PEN_FLAG_BARREL = 0x1
_PEN_FLAG_INVERTED = 0x2
_PEN_FLAG_ERASER = 0x4

# The system cursor for each cursor WebView2 asks for. A custom cursor (CSS
# `cursor: url(...)`) has no system equivalent and shows as the arrow.
_SYSTEM_CURSORS = {
    CoreCursorType.ARROW: 32512,  # IDC_ARROW
    CoreCursorType.CROSS: 32515,  # IDC_CROSS
    CoreCursorType.HAND: 32649,  # IDC_HAND
    CoreCursorType.HELP: 32651,  # IDC_HELP
    CoreCursorType.IBEAM: 32513,  # IDC_IBEAM
    CoreCursorType.SIZE_ALL: 32646,  # IDC_SIZEALL
    CoreCursorType.SIZE_NORTHEAST_SOUTHWEST: 32643,  # IDC_SIZENESW
    CoreCursorType.SIZE_NORTH_SOUTH: 32645,  # IDC_SIZENS
    CoreCursorType.SIZE_NORTHWEST_SOUTHEAST: 32642,  # IDC_SIZENWSE
    CoreCursorType.SIZE_WEST_EAST: 32644,  # IDC_SIZEWE
    CoreCursorType.UNIVERSAL_NO: 32648,  # IDC_NO
    CoreCursorType.UP_ARROW: 32516,  # IDC_UPARROW
    CoreCursorType.WAIT: 32514,  # IDC_WAIT
    CoreCursorType.PIN: 32671,  # IDC_PIN
    CoreCursorType.PERSON: 32672,  # IDC_PERSON
}
_GWL_STYLE = -16

_SW_HIDE = 0
_SW_SHOWNORMAL = 1
_SW_SHOWMINIMIZED = 2
_SW_SHOWMAXIMIZED = 3
_SW_SHOWNOACTIVATE = 4
_SW_SHOW = 5
_SW_MINIMIZE = 6
_SW_SHOWMINNOACTIVE = 7
_SW_SHOWNA = 8
_SW_RESTORE = 9

_SWP_NOSIZE = 0x0001
_SWP_NOMOVE = 0x0002
_SWP_NOZORDER = 0x0004
_SWP_NOACTIVATE = 0x0010
_SWP_FRAMECHANGED = 0x0020
_SWP_NOOWNERZORDER = 0x0200
_HWND_TOP = 0
_HWND_TOPMOST = -1
_HWND_NOTOPMOST = -2

_MF_STRING = 0x0000
_MF_POPUP = 0x0010
_MF_SEPARATOR = 0x0800

_MONITOR_DEFAULTTONEAREST = 2
_MONITOR_DEFAULTTOPRIMARY = 1
_MONITORINFOF_PRIMARY = 1
_MDT_EFFECTIVE_DPI = 0

_IMAGE_ICON = 1
_LR_LOADFROMFILE = 0x0010
_ICON_SMALL = 0
_ICON_BIG = 1
_SM_CXICON = 11
_SM_CYICON = 12
_SM_CXSMICON = 49
_SM_CYSMICON = 50
_IDC_ARROW = 32512
_CS_HREDRAW = 0x0002
_CS_VREDRAW = 0x0001
_CS_DBLCLKS = 0x0008

_WINDOW_CLASS = 'pywebview.Win32WebView2'


def _loword(value: int) -> int:
    return value & 0xFFFF


def _hiword(value: int) -> int:
    return (value >> 16) & 0xFFFF


def _monitor_info(monitor: int) -> _MONITORINFO:
    info = _MONITORINFO()
    info.cbSize = ctypes.sizeof(_MONITORINFO)
    if not _GetMonitorInfoW(monitor, ctypes.byref(info)):
        raise WinError(ctypes.get_last_error())
    return info


def _monitor_scale(monitor: int) -> float:
    dpi_x = _UINT()
    dpi_y = _UINT()
    if _GetDpiForMonitor(monitor, _MDT_EFFECTIVE_DPI, ctypes.byref(dpi_x), ctypes.byref(dpi_y)):
        return 1.0
    return dpi_x.value / 96 if dpi_x.value else 1.0


def _primary_monitor_scale() -> float:
    """
    DPI scale of the primary monitor, the one reference scale that desktop
    coordinates (window positions, screen origins) are converted with, so
    that get_position(), move() and get_screens() agree on mixed-DPI setups.
    This is the same model the WinUI 3 backend uses.
    """
    return _monitor_scale(_MonitorFromPoint(wintypes.POINT(0, 0), _MONITOR_DEFAULTTOPRIMARY))


def _set_dpi_awareness() -> None:
    """
    Make the process per-monitor (v2) DPI aware, which is what Microsoft
    recommends for a WebView2 host: Win32 coordinates are then physical pixels
    on every monitor, and WebView2 follows each monitor's scale by itself.
    A process whose awareness is already set (by a manifest, or earlier code)
    keeps it.
    """
    per_monitor_aware_v2 = ctypes.c_void_p(-4 & (2 ** (8 * ctypes.sizeof(ctypes.c_void_p)) - 1))
    try:
        if _user32.SetProcessDpiAwarenessContext(per_monitor_aware_v2):
            return
    except AttributeError:
        pass

    with contextlib.suppress(OSError, AttributeError):
        _shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE


def _pickers_unavailable() -> bool:
    """
    Windows.Storage.Pickers fail in an elevated process, so file dialogs then
    use the Win32 IFileDialog instead.
    """
    return bool(_IsUserAnAdmin())


def _parse_hex_color(hex_color: str) -> tuple[int, int, int]:
    c = hex_color.lstrip('#')
    if len(c) == 3:
        c = ''.join(channel * 2 for channel in c)
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


# ── UI-thread dispatching ────────────────────────────────────────────────────

_dispatcher_controller: DispatcherQueueController | None = None
_dispatcher_queue: DispatcherQueue | None = None
_ui_thread_id = 0
# The Compositor transparent windows share. It needs the DispatcherQueue
# above, so it is made on the UI thread, the first time one is needed.
_compositor: Compositor | None = None


def _get_compositor() -> Compositor:
    global _compositor

    if _compositor is None:
        _compositor = Compositor()
    return _compositor


def _enqueue(callback: Callable[[], None]) -> bool:
    """
    Enqueue ``callback`` on the UI thread's DispatcherQueue, which the message
    loop pumps. Returns False if the queue is gone or rejected it (the UI
    thread is shutting down); callers then release whatever waits on it.
    """
    queue = _dispatcher_queue
    if queue is not None and queue.try_enqueue(callback):
        return True
    logger.error('Failed to enqueue dispatcher callback')
    return False


def _has_ui_thread_access() -> bool:
    queue = _dispatcher_queue
    return queue is not None and queue.has_thread_access


def _guard_future_callback(callback: Callable[[], None], future: Future):
    """Transfer synchronous dispatcher callback failures to its waiting future."""

    def guarded_callback():
        try:
            callback()
        except BaseException as ex:
            if not future.done():
                future.set_exception(ex)

    return guarded_callback


def _run_dispatched(
    callback: Callable[[], None], future: Future, may_complete_synchronously: bool = False
):
    """
    Run ``callback`` (which must eventually resolve ``future``) on the UI
    thread and return its result.

    On the UI thread itself (a menu action does not run there, but a native
    callback could), blocking on ``future`` would deadlock the queue that has
    to deliver it. Only a callback that resolves ``future`` before returning -
    a Win32 IFileDialog, which pumps its own modal loop - is run inline then;
    anything else raises before it starts, so no dialog is left on screen
    whose result nobody can receive.
    """
    if _has_ui_thread_access():
        if not may_complete_synchronously:
            raise RuntimeError(
                'This operation cannot be started synchronously from the UI thread: it '
                'only resolves later, and this thread cannot wait for that without '
                'deadlocking the dispatcher that must deliver it.'
            )
        _guard_future_callback(callback, future)()
        if future.done():
            return future.result()
        raise RuntimeError(
            'This operation was started, but its result cannot be awaited '
            'synchronously from the UI thread without deadlocking the dispatcher.'
        )

    if not _enqueue(_guard_future_callback(callback, future)):
        return None

    wait([future])
    return future.result()


def _format_cookie_expiry(expires: float, is_session: bool) -> str | None:
    """
    Convert CoreWebView2Cookie.expires (seconds since the Unix epoch) to the
    HTTP-date format the cookie's Expires attribute requires. A session cookie
    is identified by is_session, the documented flag, not by a sentinel value.
    """
    if is_session or expires is None:
        return None
    return format_datetime(datetime.fromtimestamp(expires, tz=timezone.utc), usegmt=True)


def _show_message_dialog(
    hwnd: int,
    message: str,
    title: str | None,
    buttons: Sequence[str],
    on_result: Callable[[int | None], None] | None = None,
) -> None:
    """
    Show a Windows.UI.Popups.MessageDialog owned by ``hwnd`` and call
    ``on_result`` on the UI thread with the index of the button chosen, or None
    if the dialog was dismissed without one or failed. Must run on the UI
    thread. The dialog completes on a worker thread, where the window cannot
    be destroyed, so the result is enqueued back.
    """
    dialog = MessageDialog(message, title) if title is not None else MessageDialog(message)
    initialize_with_window(dialog, hwnd)

    commands = [UICommand(label) for label in buttons]
    for command in commands:
        dialog.commands.append(command)
    dialog.default_command_index = 0
    dialog.cancel_command_index = len(commands) - 1

    op = dialog.show_async()

    def on_completed(op: IAsyncOperation[IUICommand], status: AsyncStatus):
        index: int | None = None
        try:
            if status == AsyncStatus.ERROR:
                logger.error('Error showing MessageDialog: %r', WinError(op.error_code))
            elif status == AsyncStatus.COMPLETED:
                chosen = op.get_results()
                if chosen is not None:
                    labels = [command.label for command in commands]
                    if chosen.label in labels:
                        index = labels.index(chosen.label)
        finally:
            if on_result is not None:
                callback = on_result
                if not _enqueue(lambda: callback(index)):
                    callback(index)

    op.completed = on_completed


# ── WebView2 ─────────────────────────────────────────────────────────────────


class Win32EdgeChrome(WebView2Core):
    def __init__(self, form: 'BrowserView.BrowserForm', window: _Window, cache_dir: str):
        super().__init__(window)

        self.form = form
        self._drag_hwnd = form.hwnd
        self.user_data_folder = cache_dir
        self.controller: CoreWebView2Controller | None = None
        # Set for a transparent window, which WebView2 renders into a
        # composition visual instead of a child window of its own.
        self.composition_controller: CoreWebView2CompositionController | None = None
        self._window_target: DesktopWindowTarget | None = None
        # Hands what is dragged over a transparent window to its WebView2.
        self._drop_target: DropTarget | None = None
        # Makes the pointer info that a visually hosted WebView2 is sent
        # touch and pen in.
        self.environment: CoreWebView2Environment | None = None
        self.webview: CoreWebView2 | None = None
        self._js_result_semaphores: set[Semaphore] = set()
        self._js_result_lock = Lock()
        self._is_ready = False
        self._pending_load: tuple[str, str, str] | None = None

        r, g, b = _parse_hex_color(window.background_color)
        self._transparent = window.transparent
        self._background_color = Color(0, 0, 0, 0) if window.transparent else Color(255, r, g, b)

        env_options = CoreWebView2EnvironmentOptions()
        env_options.additional_browser_arguments = self._build_browser_args()

        runtime_path = webview_settings['WEBVIEW2_RUNTIME_PATH']
        if runtime_path and not os.path.isabs(runtime_path):
            runtime_path = os.path.join(get_app_root(), runtime_path)
        if runtime_path and not os.path.exists(runtime_path):
            logger.warning(
                'Custom WebView2 runtime path does not exist: %s. Using system WebView2.',
                runtime_path,
            )
            runtime_path = ''
        elif runtime_path:
            logger.debug('Using custom WebView2 runtime: %s', runtime_path)

        env_op = CoreWebView2Environment.create_with_options_async(
            runtime_path or '', cache_dir, env_options
        )

        # Only the master window's WebView2 gates app-wide readiness; a
        # secondary window's failure closes that window alone.
        is_master = window.uid == 'master'

        def fail(error: BaseException) -> None:
            if form.destroyed:
                # Closed while WebView2 was starting, which is what failed;
                # the window has already been dealt with.
                logger.debug('WebView2 creation ended with the window closed: %s', error)
                return

            if is_master:
                _fail_main_window_creation(error)
            else:
                _fail_child_window_creation(form)

        def on_env_op_completed(op: IAsyncOperation[CoreWebView2Environment], status: AsyncStatus):
            if status != AsyncStatus.COMPLETED:
                error = _async_creation_error('CoreWebView2Environment', op, status)
                logger.error('%s', error)
                fail(error)
                return

            if form.destroyed:
                return

            try:
                env = op.get_results()

                ctrl_options = env.create_core_webview2_controller_options()
                ctrl_options.is_in_private_mode_enabled = _state['private_mode']

                parent = CoreWebView2ControllerWindowReference.create_from_window_handle(form.hwnd)
                if self._transparent:
                    # Windowed hosting draws into a child window that can
                    # only show its parent through; visual hosting
                    # composes the page, alpha and all, onto the desktop.
                    ctrl_op = env.create_core_webview2_composition_controller_async(
                        parent, ctrl_options
                    )
                else:
                    ctrl_op = env.create_core_webview2_controller_async(parent, ctrl_options)
            except BaseException as error:
                logger.exception('Error setting up CoreWebView2 environment')
                fail(error)
                return

            def on_ctrl_op_completed(
                op: IAsyncOperation[CoreWebView2Controller]
                | IAsyncOperation[CoreWebView2CompositionController],
                status: AsyncStatus,
            ):
                if status != AsyncStatus.COMPLETED:
                    error = _async_creation_error('CoreWebView2Controller', op, status)
                    logger.error('%s', error)
                    fail(error)
                    return

                try:
                    controller = op.get_results()

                    if form.destroyed:
                        # The window was closed while WebView2 was starting.
                        controller.close()
                        return

                    self._on_controller_created(controller)
                except BaseException as error:
                    logger.exception('Error setting up CoreWebView2')
                    fail(error)
                    return

                _main_window_created.set()

            ctrl_op.completed = on_ctrl_op_completed

        env_op.completed = on_env_op_completed

    def _on_controller_created(self, controller: CoreWebView2Controller) -> None:
        self.controller = controller
        controller.default_background_color = self._background_color

        if isinstance(controller, CoreWebView2CompositionController):
            self.composition_controller = controller

            # The window has no redirection surface; a composition visual
            # tree, sized with it, is all that is drawn in its client area.
            compositor = _get_compositor()
            self._window_target = create_desktop_window_target(compositor, self.form.hwnd)
            root = compositor.create_container_visual()
            root.relative_size_adjustment = (1, 1)
            self._window_target.root = root
            controller.root_visual_target = root

            controller.add_cursor_changed(self.on_cursor_changed)
            try:
                self._drop_target = register_drop_target(controller, self.form.hwnd)
            except OSError as error:
                logger.warning('Drag and drop will not work in this window: %s', error)
            self.environment = controller.core_webview2.environment

        core = controller.core_webview2
        self.webview = core

        self.form.update_webview_bounds()
        self.form.update_webview_visibility()

        core.add_navigation_completed(self.on_navigation_completed)
        core.add_web_message_received(self.on_script_notify)
        core.add_source_changed(self.on_source_changed)
        core.add_new_window_requested(self.on_new_window_request)
        core.add_web_resource_requested_filter('*', CoreWebView2WebResourceContext.ALL)
        core.add_web_resource_response_received(self.on_web_resource_response)
        core.add_web_resource_requested(self.on_web_resource_request)

        if self._should_ignore_ssl():
            core.add_server_certificate_error_detected(self.on_certificate_error)

        core.add_download_starting(self.on_download_starting)
        core.add_process_failed(self.on_process_failed)

        self._apply_settings(core.settings)

        if _state['private_mode']:
            # cookies persist even if UserDataFolder is in memory. We have to delete cookies manually.
            core.cookie_manager.delete_all_cookies()

        pending_load = self._pending_load
        self._pending_load = None
        self._is_ready = True

        if pending_load:
            kind, content, base_uri = pending_load
        else:
            kind, content = self._get_initial_load()
            base_uri = ''

        if kind == 'url':
            self.load_url(content)
        else:
            self.load_html(content, base_uri)

        if _GetFocus() == self.form.hwnd:
            controller.move_focus(CoreWebView2MoveFocusReason.PROGRAMMATIC)

        if _state['debug'] and webview_settings['OPEN_DEVTOOLS_IN_DEBUG']:
            core.open_dev_tools_window()

    def close(self) -> int:
        """Close the controller and return the browser process id, or 0."""
        process_id = 0
        controller = self.controller
        window_target = self._window_target
        drop_target = self._drop_target
        self.controller = None
        self.composition_controller = None
        self._window_target = None
        self._drop_target = None
        self.environment = None
        self.webview = None

        # Each is closed even if closing another raises.
        with contextlib.ExitStack() as stack:
            if window_target is not None:
                stack.callback(window_target.close)
            if drop_target is not None:
                stack.enter_context(drop_target)
            if controller is not None:
                with contextlib.suppress(OSError):
                    process_id = int(controller.core_webview2.browser_process_id)
                controller.close()

        return process_id

    def on_cursor_changed(self, sender: CoreWebView2CompositionController, _) -> None:
        # Only while the pointer is over the page: the change can come after
        # it has moved onto a border, whose sizing cursor must stay.
        if self.form.pointer_in_client():
            self.form.update_cursor()

    def system_cursor(self) -> int:
        """The system cursor (IDC_*) for what the page asks for, or the arrow."""
        controller = self.composition_controller
        if controller is None:
            return _IDC_ARROW
        try:
            cursor = controller.cursor
        except OSError:
            return _IDC_ARROW
        if cursor is None:
            return _IDC_ARROW
        return _SYSTEM_CURSORS.get(cursor.type, _IDC_ARROW)

    def evaluate_js(self, script: str, parse_json: bool):
        result = None
        semaphore = Semaphore(0)
        with self._js_result_lock:
            self._js_result_semaphores.add(semaphore)

        def _callback(res: str | None):
            nonlocal result

            if parse_json and res is not None:
                try:
                    result = json.loads(res)
                except Exception:
                    result = res
            else:
                result = res

            semaphore.release()

        def callback():
            try:
                if self.webview is None:
                    _callback(None)
                    return

                op = self.webview.execute_script_async(script)

                def on_completed(op: IAsyncOperation[str], status: AsyncStatus):
                    if status == AsyncStatus.ERROR:
                        logger.error('Error executing script: %r', WinError(op.error_code))
                        _callback(None)
                    elif status == AsyncStatus.CANCELED:
                        _callback(None)
                    elif status == AsyncStatus.COMPLETED:
                        try:
                            _callback(json.loads(op.get_results()))
                        except Exception:
                            logger.exception('Error parsing script result')
                            _callback(None)

                op.completed = on_completed
            except Exception:
                logger.exception('Error occurred in script')
                _callback(None)

        try:
            if _has_ui_thread_access():
                # evaluate_js() needs its result, and blocking here would
                # deadlock the dispatcher that delivers it, so it raises
                # before starting the script. run_js() is fire-and-forget.
                if parse_json:
                    raise RuntimeError(
                        'evaluate_js() cannot return a result synchronously when called '
                        'from the UI thread without deadlocking the dispatcher that must '
                        'deliver it.'
                    )
                callback()
                return None

            if not _enqueue(callback):
                return None

            semaphore.acquire()
            return result
        finally:
            with self._js_result_lock:
                self._js_result_semaphores.discard(semaphore)

    def release_pending_js_results(self):
        with self._js_result_lock:
            semaphores = tuple(self._js_result_semaphores)

        for semaphore in semaphores:
            semaphore.release()

    def clear_cookies(self):
        if self.webview is not None:
            self.webview.cookie_manager.delete_all_cookies()

    def get_cookies(self, cookies: list[SimpleCookie], semaphore: Semaphore):
        if self.webview is None:
            semaphore.release()
            return

        def _parse_cookies(_cookies: Sequence[CoreWebView2Cookie]):
            # cookies must be accessed in the main thread, otherwise an exception is thrown
            # https://github.com/MicrosoftEdge/WebView2Feedback/issues/1976
            try:
                for c in _cookies:
                    try:
                        # NONE is an explicit SameSite=None policy, so it maps
                        # to 'none', not to Python None.
                        same_site = CoreWebView2CookieSameSiteKind(c.same_site).name.lower()
                        data = {
                            'name': c.name,
                            'value': c.value,
                            'path': c.path,
                            'domain': c.domain,
                            'expires': _format_cookie_expiry(c.expires, c.is_session),
                            'secure': c.is_secure,
                            'httponly': c.is_http_only,
                            'samesite': same_site,
                        }

                        cookies.append(create_cookie(data))
                    except Exception as e:
                        logger.exception(e)
            finally:
                semaphore.release()

        try:
            op = self.webview.cookie_manager.get_cookies_async(self.url or '')
        except Exception:
            logger.exception('Error requesting cookies')
            semaphore.release()
            return

        def on_op_completed(op: IAsyncOperation[Sequence[CoreWebView2Cookie]], status: AsyncStatus):
            try:
                if status == AsyncStatus.ERROR:
                    logger.error('Error getting cookies: %r', WinError(op.error_code))
                    semaphore.release()
                elif status == AsyncStatus.COMPLETED:
                    _cookies = op.get_results()

                    if not _enqueue(lambda: _parse_cookies(_cookies)):
                        semaphore.release()
                else:
                    semaphore.release()
            except Exception:
                logger.exception('Error in cookie completion handler')
                semaphore.release()

        op.completed = on_op_completed

    def load_html(self, content: str, base_uri: str):
        self.html = inject_base_uri(content, base_uri) if base_uri else content
        self.ishtml = True

        if not self._is_ready or self.webview is None:
            self._pending_load = ('html', content, base_uri)
            return

        self.webview.navigate_to_string(self.html)

    def load_url(self, url: str):
        self.ishtml = False

        if not self._is_ready or self.webview is None:
            self._pending_load = ('url', url, '')
            return

        self.webview.navigate(url)

    def on_certificate_error(
        self, _: CoreWebView2, args: CoreWebView2ServerCertificateErrorDetectedEventArgs
    ):
        args.action = CoreWebView2ServerCertificateErrorAction.ALWAYS_ALLOW

    def _show_alert(self, message: str):
        _show_message_dialog(
            self.form.hwnd,
            message,
            None,
            [self.pywebview_window.localization['global.ok']],
        )

    def _extract_dropped_files(self, additional_objects) -> list:
        # An element of the Object collection is a plain winrt.system.Object:
        # isinstance() tests the WinRT class, and as_() gives its members.
        files = [
            obj.as_(CoreWebView2File)
            for obj in additional_objects
            if isinstance(obj, CoreWebView2File)
        ]
        return [(os.path.basename(file.path), file.path) for file in files]

    def _apply_settings(self, settings):
        settings.are_browser_accelerator_keys_enabled = _state['debug']
        settings.are_default_context_menus_enabled = _state['debug']
        settings.are_default_script_dialogs_enabled = True
        settings.are_dev_tools_enabled = _state['debug']
        settings.is_built_in_error_page_enabled = True
        settings.is_script_enabled = True
        settings.is_web_message_enabled = True
        settings.is_status_bar_enabled = _state['debug']
        settings.is_swipe_navigation_enabled = False
        settings.is_zoom_control_enabled = True
        if _state['user_agent']:
            settings.user_agent = _state['user_agent']

    def on_script_notify(self, sender: CoreWebView2, args: CoreWebView2WebMessageReceivedEventArgs):
        try:
            self._route_script_message(args.web_message_as_json, lambda: args.additional_objects)
        except Exception:
            logger.exception('Exception occurred during on_script_notify')

    def on_new_window_request(
        self, sender: CoreWebView2, args: CoreWebView2NewWindowRequestedEventArgs
    ):
        args.handled = True
        self._handle_new_window_request(args.uri)

    def on_source_changed(self, sender: CoreWebView2, args: CoreWebView2SourceChangedEventArgs):
        source = sender.source or None

        if self.ishtml and source and source.lower() == 'about:blank':
            # navigate_to_string() (used by load_html) reports the source as
            # about:blank; don't let that clear HTML mode, or get_current_url()
            # would report 'about:blank' instead of None.
            return

        self.url = source
        self.ishtml = False

    def on_process_failed(
        self, sender: CoreWebView2, args: CoreWebView2ProcessFailedEventArgs
    ) -> None:
        if args.process_failed_kind != CoreWebView2ProcessFailedKind.BROWSER_PROCESS_EXITED:
            # The controller outlives the other processes: a page whose
            # renderer exited shows an error page, as in a browser.
            return

        # Every call into the controller now fails, so the window stops
        # making them: it stays, without its page, until it is closed.
        logger.error('The WebView2 browser process exited: %s', args.reason.name)
        controller = self.controller
        self.controller = None
        self.composition_controller = None
        if controller is not None:
            controller.close()

    def on_download_starting(
        self, sender: CoreWebView2, args: CoreWebView2DownloadStartingEventArgs
    ):
        args.cancel = True  # default: cancel; uncancelled below if user picks a file

        if not self._should_allow_download():
            return

        if _pickers_unavailable():
            # IFileSaveDialog runs its own modal loop, so this completes here.
            try:
                path = pick_save_file_win32(
                    self.form.hwnd,
                    os.path.basename(args.result_file_path),
                    [],
                    self._get_download_initial_dir(),
                )
            except Exception:
                logger.exception('Error selecting download destination')
                return
            if path:
                args.result_file_path = path
                args.cancel = False
            return

        deferral = args.get_deferral()

        try:
            picker = FileSavePicker()
            initialize_with_window(picker, self.form.hwnd)
            picker.suggested_start_location = PickerLocationId.DOWNLOADS
            picker.suggested_file_name = os.path.basename(args.result_file_path)
            picker.file_type_choices['*'] = ['.']

            operation = picker.pick_save_file_async()

            def on_completed(op: IAsyncOperation[StorageFile | None], status: AsyncStatus):
                path: str | None = None
                try:
                    if status == AsyncStatus.ERROR:
                        logger.error(
                            'Error selecting download destination: %r', WinError(op.error_code)
                        )
                    elif status == AsyncStatus.COMPLETED:
                        selected_file = op.get_results()
                        if selected_file is not None:
                            path = selected_file.path
                except Exception:
                    logger.exception('Error handling download destination')

                # The picker completes on a worker thread; WebView2's
                # event args belong to the UI thread.
                def finish() -> None:
                    try:
                        if path is not None:
                            args.result_file_path = path
                            args.cancel = False
                    finally:
                        deferral.complete()

                if not _enqueue(finish):
                    deferral.complete()

            operation.completed = on_completed
        except Exception:
            logger.exception('Error opening download destination picker')
            deferral.complete()

    def on_web_resource_response(
        self, sender: CoreWebView2, args: CoreWebView2WebResourceResponseReceivedEventArgs
    ):
        headers = {kv.key: kv.value for kv in args.response.headers}
        self._fire_response_event(args.request.uri, args.response.status_code, headers)

    def on_web_resource_request(
        self, sender: CoreWebView2, args: CoreWebView2WebResourceRequestedEventArgs
    ):
        if not len(self.pywebview_window.events.request_sent):
            return

        original_headers = {kv.key: kv.value for kv in args.request.headers}
        uri = args.request.uri
        method = args.request.method
        deferral = args.get_deferral()

        def dispatch_event():
            try:
                diff = self._compute_request_header_diff(original_headers, uri, method)
            except Exception:
                logger.exception('Error handling web resource request')
                diff = None

            def apply_header_diff():
                try:
                    if diff is not None:
                        extra, missing = diff
                        for key, value in extra.items():
                            args.request.headers.set_header(key, value)
                        for key in missing:
                            args.request.headers.remove_header(key)
                finally:
                    deferral.complete()

            if not _enqueue(apply_header_diff):
                deferral.complete()

        self._dispatch_request_event(dispatch_event)

    def on_navigation_completed(
        self, sender: CoreWebView2, _: CoreWebView2NavigationCompletedEventArgs
    ):
        self.url = None if self.ishtml else sender.source

        inject_pywebview(renderer, self.pywebview_window)


# ── Windows ──────────────────────────────────────────────────────────────────

# The form whose CreateWindowExW call is in progress. Its first messages
# (WM_NCCREATE, WM_GETMINMAXINFO, ...) arrive before CreateWindowExW returns
# the handle, so the window procedure adopts the handle for this form.
_creating_form: 'BrowserView.BrowserForm | None' = None
_forms_by_hwnd: dict[int, 'BrowserView.BrowserForm'] = {}
_window_class_registered = False


@_WNDPROC
def _window_procedure(hwnd, msg, wparam, lparam):
    form = _forms_by_hwnd.get(hwnd)

    if form is None and _creating_form is not None:
        form = _creating_form
        form.hwnd = hwnd
        _forms_by_hwnd[hwnd] = form

    if form is not None:
        try:
            result = form.handle_message(msg, wparam, lparam)
        except Exception:
            logger.exception('Error handling window message 0x%04x', msg)
            result = None

        if result is not None:
            return result

    return _DefWindowProcW(hwnd, msg, wparam, lparam)


def _register_window_class() -> None:
    global _window_class_registered

    if _window_class_registered:
        return

    wc = _WNDCLASSEXW()
    wc.cbSize = ctypes.sizeof(_WNDCLASSEXW)
    # CS_DBLCLKS: a visually hosted WebView2 is sent double clicks as such.
    wc.style = _CS_HREDRAW | _CS_VREDRAW | _CS_DBLCLKS
    wc.lpfnWndProc = _window_procedure
    wc.hInstance = _GetModuleHandleW(None)
    wc.hCursor = _LoadCursorW(None, ctypes.c_void_p(_IDC_ARROW))
    wc.lpszClassName = _WINDOW_CLASS

    if not _RegisterClassExW(ctypes.byref(wc)):
        raise WinError(ctypes.get_last_error())

    _window_class_registered = True


def _load_icons(path: str | None) -> tuple[int | None, int | None]:
    """
    Load the window's large and small icons from an .ico or .png file, or
    else from the running executable, as every other Windows app shows.
    """
    big_size = (_GetSystemMetrics(_SM_CXICON), _GetSystemMetrics(_SM_CYICON))
    small_size = (_GetSystemMetrics(_SM_CXSMICON), _GetSystemMetrics(_SM_CYSMICON))

    if path and os.path.isfile(path):
        lower = path.lower()
        if lower.endswith('.ico'):
            big = _LoadImageW(None, path, _IMAGE_ICON, *big_size, _LR_LOADFROMFILE)
            small = _LoadImageW(None, path, _IMAGE_ICON, *small_size, _LR_LOADFROMFILE)
            return big or None, small or None

        if lower.endswith('.png'):
            # CreateIconFromResourceEx takes PNG data as it is (Vista and later).
            with open(path, 'rb') as f:
                data = f.read()
            big = _CreateIconFromResourceEx(data, len(data), True, 0x00030000, *big_size, 0)
            small = _CreateIconFromResourceEx(data, len(data), True, 0x00030000, *small_size, 0)
            return big or None, small or None

        logger.warning(
            'The win32 backend supports .ico or .png window icons, got %r. '
            'Falling back to the default icon.',
            path,
        )

    big = wintypes.HICON()
    small = wintypes.HICON()
    _ExtractIconExW(sys.executable, 0, ctypes.byref(big), ctypes.byref(small), 1)
    return big.value or None, small.value or None


class BrowserView:
    instances: dict[str, 'BrowserView.BrowserForm'] = {}

    app_menu_list: Iterable[Menu] = []

    class BrowserForm:
        def __init__(self, window: _Window, cache_dir: str):
            global _creating_form

            self.uid = window.uid
            self.pywebview_window = window
            self.localization = window.localization
            self.hwnd: int = 0
            self.browser: Win32EdgeChrome | None = None
            self.destroyed = False
            self._created = False
            self._is_active = False
            self._tracking_mouse_leave = False
            # Visual hosting: the releases owed to WebView2 for the presses
            # it was sent, each with its mouse data (which X button).
            self._pressed_buttons: set[tuple[CoreWebView2MouseEventKind, int]] = set()
            self._confirming_close = False
            self._min_size = window.min_size
            self._size_kind = _SIZE_RESTORED
            self._fullscreen_restore: tuple[int, _WINDOWPLACEMENT, int] | None = None
            self._menu_actions: dict[int, MenuAction] = {}
            self._initial_show_cmd: int | None = None

            r, g, b = _parse_hex_color(window.background_color)
            self._background_brush = _CreateSolidBrush(r | (g << 8) | (b << 16))

            if window.frameless:
                style = _WS_POPUP | _WS_SYSMENU | _WS_MINIMIZEBOX
            else:
                style = _WS_OVERLAPPEDWINDOW
                if not window.resizable:
                    style &= ~(_WS_THICKFRAME | _WS_MAXIMIZEBOX)

            ex_style = 0
            if window.transparent:
                # No opaque surface of its own behind the composed page.
                ex_style |= _WS_EX_NOREDIRECTIONBITMAP
            if window.on_top:
                ex_style |= _WS_EX_TOPMOST
            if not window.focus:
                # WS_EX_NOACTIVATE alone drops the taskbar button.
                ex_style |= _WS_EX_NOACTIVATE | _WS_EX_APPWINDOW

            x, y, width, height = self._initial_geometry(window)

            _creating_form = self
            try:
                hwnd = _CreateWindowExW(
                    ex_style,
                    _WINDOW_CLASS,
                    window.title,
                    style,
                    x,
                    y,
                    width,
                    height,
                    None,
                    None,
                    _GetModuleHandleW(None),
                    None,
                )
            finally:
                _creating_form = None

            if not hwnd:
                error = WinError(ctypes.get_last_error())
                _DeleteObject(self._background_brush)
                raise error

            try:
                self._construct(window, cache_dir)
            except BaseException:
                # The caller never gets this instance, so nothing else could
                # destroy the window this already created.
                with contextlib.suppress(Exception):
                    _DestroyWindow(self.hwnd)
                raise

        def _construct(self, window: _Window, cache_dir: str) -> None:
            self.pywebview_window.native = self

            self._icons = _load_icons(_state['icon'])
            big, small = self._icons
            if big:
                _SendMessageW(self.hwnd, _WM_SETICON, _ICON_BIG, big)
            if small:
                _SendMessageW(self.hwnd, _WM_SETICON, _ICON_SMALL, small)

            if window.frameless and window.shadow and not window.transparent:
                enable_window_shadow(self.hwnd)

            menu = window.menu or _state['menu'] or BrowserView.app_menu_list
            if menu:
                self.set_window_menu(menu)

            if window.fullscreen:
                self.toggle_fullscreen()

            self.browser = Win32EdgeChrome(self, window, cache_dir)
            self._created = True

        def __str__(self):
            return f'<Window object with {self.hwnd} handle>'

        @staticmethod
        def _initial_geometry(window: _Window) -> tuple[int, int, int, int]:
            """
            The window's physical position and outer size. The size is the
            logical size scaled for the monitor the window opens on, so that is
            worked out first.
            """
            logical_width = max(window.initial_width, window.min_size[0])
            logical_height = max(window.initial_height, window.min_size[1])

            if window.initial_x is not None and window.initial_y is not None:
                # initial_x/y are desktop-wide logical coordinates, the space
                # get_screens() reports origins in.
                primary_scale = _primary_monitor_scale()
                x = int(window.initial_x * primary_scale)
                y = int(window.initial_y * primary_scale)
                monitor = _MonitorFromPoint(wintypes.POINT(x, y), _MONITOR_DEFAULTTONEAREST)
                scale = _monitor_scale(monitor)
                return x, y, int(logical_width * scale), int(logical_height * scale)

            if window.screen is not None and window.screen.frame:
                # get_screens() puts the HMONITOR in frame.
                monitor = cast(int, window.screen.frame)
            else:
                # Like WinForms' CenterScreen: the monitor the user is on.
                cursor = wintypes.POINT()
                _GetCursorPos(ctypes.byref(cursor))
                monitor = _MonitorFromPoint(cursor, _MONITOR_DEFAULTTOPRIMARY)

            scale = _monitor_scale(monitor)
            width = int(logical_width * scale)
            height = int(logical_height * scale)
            work = _monitor_info(monitor).rcWork
            x = work.left + (work.right - work.left - width) // 2
            y = work.top + (work.bottom - work.top - height) // 2
            return x, y, width, height

        @property
        def _scale(self) -> float:
            """Logical-to-physical pixel scale of the monitor this window is on."""
            dpi = _GetDpiForWindow(self.hwnd) if self.hwnd else 0
            return dpi / 96 if dpi else 1.0

        # ── Window procedure ─────────────────────────────────────────────

        def handle_message(self, msg: int, wparam: int, lparam: int) -> int | None:
            """Handle a window message; None means DefWindowProcW's default."""
            if msg in _FORWARDED_MOUSE_MESSAGES:
                if self._forward_mouse(msg, wparam, lparam):
                    return 0
                return None

            if msg in _FORWARDED_POINTER_MESSAGES:
                if self._forward_pointer(msg, wparam, lparam):
                    return 0
                return None

            if msg == _WM_CAPTURECHANGED:
                # lparam is the window that has the mouse now.
                if lparam != self.hwnd:
                    self._on_capture_lost()
                return 0

            if msg == _WM_SETCURSOR:
                if _loword(lparam) == _HTCLIENT and self._is_visually_hosted():
                    self.update_cursor()
                    return 1
                return None

            if msg == _WM_GETMINMAXINFO:
                info = _MINMAXINFO.from_address(lparam)
                scale = self._scale
                info.ptMinTrackSize.x = max(info.ptMinTrackSize.x, int(self._min_size[0] * scale))
                info.ptMinTrackSize.y = max(info.ptMinTrackSize.y, int(self._min_size[1] * scale))
                return 0

            if msg == _WM_DPICHANGED:
                suggested = wintypes.RECT.from_address(lparam)
                _SetWindowPos(
                    self.hwnd,
                    None,
                    suggested.left,
                    suggested.top,
                    suggested.right - suggested.left,
                    suggested.bottom - suggested.top,
                    _SWP_NOZORDER | _SWP_NOACTIVATE,
                )
                return 0

            if msg == _WM_SIZE:
                self._on_size(wparam)
                return 0

            if msg == _WM_MOVE:
                self._on_move()
                return 0

            if msg == _WM_ACTIVATE:
                self._on_activate(_loword(wparam) != _WA_INACTIVE)
                return None

            if msg == _WM_SETFOCUS:
                controller = self.browser.controller if self.browser else None
                if controller is not None:
                    controller.move_focus(CoreWebView2MoveFocusReason.PROGRAMMATIC)
                return 0

            if msg == _WM_ERASEBKGND:
                # A transparent window has nothing to erase: what it shows is
                # composed, and GDI would draw into a surface it lacks.
                if not self.pywebview_window.transparent:
                    rect = wintypes.RECT()
                    _GetClientRect(self.hwnd, ctypes.byref(rect))
                    _FillRect(wparam, ctypes.byref(rect), self._background_brush)
                return 1

            if msg == _WM_COMMAND:
                # A menu item: high word 0, no control handle.
                if _hiword(wparam) == 0 and not lparam:
                    action = self._menu_actions.get(_loword(wparam))
                    if action is not None:
                        # Don't run the action function on the UI thread.
                        threading.Thread(target=action.function).start()
                        return 0
                return None

            if msg == _WM_CLOSE:
                # Always 0: DefWindowProcW would destroy the window, skipping
                # the `closing` event and the confirmation that just failed.
                try:
                    if self._begin_close():
                        _DestroyWindow(self.hwnd)
                except Exception:
                    logger.exception('Error closing window')
                return 0

            if msg == _WM_ENDSESSION:
                # Windows is logging off or shutting down: nothing can veto
                # that, but `closed` still fires and the WebView2 is closed.
                if wparam and not self.destroyed:
                    _DestroyWindow(self.hwnd)
                return 0

            if msg == _WM_DESTROY:
                self._on_destroy()
                return 0

            if msg == _WM_NCDESTROY:
                self._on_nc_destroy()
                return None

            return None

        def _is_visually_hosted(self) -> bool:
            return self.browser is not None and self.browser.composition_controller is not None

        def _forward_mouse(self, msg: int, wparam: int, lparam: int) -> bool:
            """
            Send a mouse message to a visually hosted WebView2, which, unlike
            a windowed one, has no window of its own to receive it. Returns
            False if there is none to send it to.
            """
            controller = self.browser.composition_controller if self.browser else None
            if controller is None:
                return False

            if msg == _WM_MOUSELEAVE:
                self._tracking_mouse_leave = False
                controller.send_mouse_input(
                    CoreWebView2MouseEventKind.LEAVE,
                    CoreWebView2MouseEventVirtualKeys.NONE,
                    0,
                    (0, 0),
                )
                return True

            point = wintypes.POINT(
                ctypes.c_short(_loword(lparam)).value, ctypes.c_short(_hiword(lparam)).value
            )
            mouse_data = 0

            if msg in (_WM_MOUSEWHEEL, _WM_MOUSEHWHEEL):
                # Wheel messages carry screen coordinates and a signed delta.
                _ScreenToClient(self.hwnd, ctypes.byref(point))
                mouse_data = ctypes.c_short(_hiword(wparam)).value & 0xFFFFFFFF
                # The wheel may go to the focused window wherever the
                # pointer is; the page gets it only over the page, or
                # mid-drag.
                client = wintypes.RECT()
                _GetClientRect(self.hwnd, ctypes.byref(client))
                inside = 0 <= point.x < client.right and 0 <= point.y < client.bottom
                if not inside and _GetCapture() != self.hwnd:
                    return False
            elif msg in _X_BUTTON_MESSAGES:
                mouse_data = _hiword(wparam)  # XBUTTON1 or XBUTTON2

            if msg == _WM_MOUSEMOVE and not self._tracking_mouse_leave:
                # Ask for the WM_MOUSELEAVE that tells WebView2 the pointer left.
                track = _TRACKMOUSEEVENT()
                track.cbSize = ctypes.sizeof(_TRACKMOUSEEVENT)
                track.dwFlags = _TME_LEAVE
                track.hwndTrack = self.hwnd
                self._tracking_mouse_leave = bool(_TrackMouseEvent(ctypes.byref(track)))

            keys = _loword(wparam)

            if msg in _BUTTON_RELEASES:
                # Keep receiving the mouse while a button drags outside the window.
                self._pressed_buttons.add((_BUTTON_RELEASES[msg], mouse_data))
                _SetCapture(self.hwnd)
            elif msg in _BUTTON_UP_MESSAGES:
                self._pressed_buttons.discard((CoreWebView2MouseEventKind(msg), mouse_data))

            try:
                controller.send_mouse_input(
                    CoreWebView2MouseEventKind(msg),
                    CoreWebView2MouseEventVirtualKeys(keys),
                    mouse_data,
                    (point.x, point.y),
                )
            finally:
                # Released only after the release is sent, so that the
                # WM_CAPTURECHANGED this causes finds no button still pressed.
                if msg in _BUTTON_UP_MESSAGES and not keys & _MK_BUTTONS:
                    if _GetCapture() == self.hwnd:
                        _ReleaseCapture()

            return True

        def _forward_pointer(self, msg: int, wparam: int, lparam: int) -> bool:
            """
            Send a touch or pen message to a visually hosted WebView2, so that
            the page scrolls, zooms and gets touch and pen pointer events as
            a windowed one does, rather than the mouse messages Windows would
            make of it. Returns False if there is none to send it to, and for
            a mouse, which comes as mouse messages.
            """
            browser = self.browser
            controller = browser.composition_controller if browser else None
            environment = browser.environment if browser else None
            if controller is None or environment is None:
                return False

            pointer_id = _loword(wparam)
            current = PointerPoint.get_current_point(pointer_id)
            device_type = current.pointer_device.pointer_device_type
            if device_type not in (PointerDeviceType.TOUCH, PointerDeviceType.PEN):
                return False

            # WebView2 takes physical pixels from its own corner, which is the
            # client area's. The message has the location in screen pixels;
            # PointerPoint has it and the contact in device-independent pixels.
            point = wintypes.POINT(
                ctypes.c_short(_loword(lparam)).value, ctypes.c_short(_hiword(lparam)).value
            )
            _ScreenToClient(self.hwnd, ctypes.byref(point))
            x, y = point.x, point.y
            scale = self._scale
            position = current.position
            raw = current.raw_position
            raw_x = x + (raw.x - position.x) * scale
            raw_y = y + (raw.y - position.y) * scale

            def to_pixels(rect: Rect, at_x: float, at_y: float) -> Rect:
                return Rect(
                    at_x + (rect.x - position.x) * scale,
                    at_y + (rect.y - position.y) * scale,
                    rect.width * scale,
                    rect.height * scale,
                )

            properties = current.properties
            info = environment.create_core_webview2_pointer_info()
            info.pointer_kind = _PT_PEN if device_type == PointerDeviceType.PEN else _PT_TOUCH
            info.pointer_id = pointer_id
            info.frame_id = current.frame_id
            info.pointer_flags = _hiword(wparam) | _POINTER_EVENT_FLAGS.get(
                msg, _POINTER_FLAG_UPDATE
            )
            info.pixel_location = (x, y)
            info.pixel_location_raw = (raw_x, raw_y)
            info.time = _GetMessageTime() & 0xFFFFFFFF
            info.history_count = 1
            # POINTER_BUTTON_CHANGE_TYPE is numbered as PointerUpdateKind is.
            info.button_change_kind = int(properties.pointer_update_kind)

            # PointerPoint's pressure goes from 0 to 1, Win32's to 1024.
            pressure = round(properties.pressure * 1024)
            if device_type == PointerDeviceType.PEN:
                info.pen_flags = (
                    (_PEN_FLAG_BARREL if properties.is_barrel_button_pressed else 0)
                    | (_PEN_FLAG_INVERTED if properties.is_inverted else 0)
                    | (_PEN_FLAG_ERASER if properties.is_eraser else 0)
                )
                info.pen_mask = _PEN_MASK_ALL
                info.pen_pressure = pressure
                info.pen_rotation = round(properties.twist) % 360
                info.pen_tilt_x = round(properties.x_tilt)
                info.pen_tilt_y = round(properties.y_tilt)
            else:
                info.touch_mask = _TOUCH_MASK_ALL
                info.touch_contact = to_pixels(properties.contact_rect, x, y)
                info.touch_contact_raw = to_pixels(properties.contact_rect_raw, raw_x, raw_y)
                info.touch_orientation = round(properties.orientation) % 360
                info.touch_pressure = pressure

            controller.send_pointer_input(CoreWebView2PointerEventKind(msg), info)
            return True

        def _on_capture_lost(self) -> None:
            """
            The mouse was taken away mid-press: by a window drag (easy_drag
            hands the press to Windows' move loop), Alt+Tab or a menu. The
            release never comes here, so WebView2 is sent one, or the page
            would go on acting as if the button were held.
            """
            pressed = self._pressed_buttons
            self._pressed_buttons = set()
            if not pressed:
                return

            def release() -> None:
                controller = self.browser.composition_controller if self.browser else None
                if controller is None:
                    return
                for kind, mouse_data in pressed:
                    controller.send_mouse_input(
                        kind,
                        CoreWebView2MouseEventVirtualKeys.NONE,
                        mouse_data,
                        _RELEASE_OUTSIDE_POINT,
                    )

            # Later, from the message loop, not from inside the capture change.
            _enqueue(release)

        def pointer_in_client(self) -> bool:
            """Whether the pointer is over this window's client area."""
            cursor = wintypes.POINT()
            _GetCursorPos(ctypes.byref(cursor))
            # Not over another window on top of this one, such as another
            # pywebview window, which shares this thread's cursor.
            if _GetAncestor(_WindowFromPoint(cursor), _GA_ROOT) != self.hwnd:
                return False
            position = ((cursor.y & 0xFFFF) << 16) | (cursor.x & 0xFFFF)
            return _SendMessageW(self.hwnd, _WM_NCHITTEST, 0, position) == _HTCLIENT

        def update_cursor(self) -> None:
            if self.browser is not None:
                _SetCursor(_LoadCursorW(None, ctypes.c_void_p(self.browser.system_cursor())))

        def update_webview_bounds(self) -> None:
            controller = self.browser.controller if self.browser else None
            if controller is None:
                return

            rect = wintypes.RECT()
            _GetClientRect(self.hwnd, ctypes.byref(rect))
            controller.bounds = (0, 0, rect.right - rect.left, rect.bottom - rect.top)

        def update_webview_visibility(self) -> None:
            controller = self.browser.controller if self.browser else None
            if controller is None:
                return

            # A hidden or minimized WebView2 can stop rendering to save resources.
            controller.is_visible = bool(_IsWindowVisible(self.hwnd)) and not _IsIconic(self.hwnd)

        def _on_size(self, kind: int) -> None:
            if kind not in (_SIZE_RESTORED, _SIZE_MINIMIZED, _SIZE_MAXIMIZED):
                return

            self.update_webview_bounds()
            self.update_webview_visibility()

            previous = self._size_kind
            self._size_kind = kind

            if not self._created:
                return

            events = self.pywebview_window.events
            if kind != previous:
                if kind == _SIZE_MAXIMIZED:
                    events.maximized.set()
                elif kind == _SIZE_MINIMIZED:
                    events.minimized.set()
                else:
                    events.restored.set()

            if kind != _SIZE_MINIMIZED:
                events.resized.set(*self.get_size())

        def _on_move(self) -> None:
            controller = self.browser.controller if self.browser else None
            if controller is not None:
                controller.notify_parent_window_position_changed()

            if self._created and not _IsIconic(self.hwnd):
                self.pywebview_window.events.moved.set(*self.get_position())

        def _on_activate(self, active: bool) -> None:
            self._is_active = active

            if active and self._created and not self.pywebview_window.events.shown.is_set():
                self.pywebview_window.events.shown.set()

        def _begin_close(self) -> bool:
            """
            Fire the `closing` event and, if needed, the confirmation dialog.
            Returns False if the close should not proceed yet. Shared by
            WM_CLOSE and `close` so both fire the same events.
            """
            if self._confirming_close:
                return False

            if self.pywebview_window.events.closing.set():
                return False

            if self.pywebview_window.confirm_close:
                self._confirming_close = True

                def on_result(index: int | None) -> None:
                    self._confirming_close = False
                    if index == 0 and not self.destroyed:
                        _DestroyWindow(self.hwnd)

                try:
                    _show_message_dialog(
                        self.hwnd,
                        self.localization['global.quitConfirmation'],
                        self.pywebview_window.title,
                        [self.localization['global.ok'], self.localization['global.cancel']],
                        on_result,
                    )
                except BaseException:
                    # No dialog will answer, so the next close must ask again.
                    self._confirming_close = False
                    raise

                # The window stays until the dialog answers.
                return False

            return True

        def _on_destroy(self) -> None:
            self.destroyed = True

            if self.uid == 'master' and not _main_window_created.is_set():
                # The master window can close before WebView2 finishes
                # initializing. Without this, a thread blocked in
                # _wait_for_main_window() for a child window would never wake.
                _fail_main_window_creation(
                    RuntimeError('Main window was closed before initialization completed'),
                    closed_early=True,
                )

            # Whatever goes wrong here, the window must still be unregistered,
            # `closed` must fire and the last window must end the loop.
            process_id = 0
            if self.browser is not None:
                try:
                    self.browser.release_pending_js_results()
                    process_id = self.browser.close()
                except Exception:
                    logger.exception('Error closing WebView2')

            # pop: a form whose construction failed was never registered.
            BrowserView.instances.pop(self.uid, None)

            if self.pywebview_window in windows:
                windows.remove(self.pywebview_window)

            self.pywebview_window.events.closed.set()

            if len(BrowserView.instances) == 0:
                if _state['private_mode'] and self.browser is not None:
                    # clear_user_data() waits on the browser process before
                    # deleting the folder, so it runs on its own thread;
                    # create_window() joins it before returning.
                    global _private_cleanup_thread
                    _private_cleanup_thread = threading.Thread(
                        target=self.browser.clear_user_data, args=(process_id,), daemon=True
                    )
                    _private_cleanup_thread.start()

                _PostQuitMessage(0)

        def _on_nc_destroy(self) -> None:
            _forms_by_hwnd.pop(self.hwnd, None)

            # A menu bar detached for fullscreen is not destroyed with the window.
            if self._fullscreen_restore is not None and self._fullscreen_restore[2]:
                _DestroyMenu(self._fullscreen_restore[2])
                self._fullscreen_restore = None

            for icon in getattr(self, '_icons', ()):
                if icon:
                    _DestroyIcon(icon)
            self._icons = (None, None)

            if self._background_brush:
                _DeleteObject(self._background_brush)
                self._background_brush = None

        # ── Public operations ────────────────────────────────────────────

        def evaluate_js(self, script: str, parse_json: bool):
            if self.browser is None:
                return None
            return self.browser.evaluate_js(script, parse_json)

        @staticmethod
        def invoke_on_ui_thread(func):
            def wrapper(self: 'BrowserView.BrowserForm', *args, **kwargs):
                if _has_ui_thread_access():
                    return func(self, *args, **kwargs)

                event = Event()
                result = None
                exception = None

                def invoke():
                    nonlocal result, exception

                    try:
                        result = func(self, *args, **kwargs)
                    except BaseException as ex:
                        exception = ex
                    finally:
                        event.set()

                if not _enqueue(invoke):
                    raise RuntimeError('Failed to enqueue dispatcher callback')

                event.wait()

                if exception is not None:
                    raise exception

                return result

            return wrapper

        def show_initial(self, window: _Window) -> None:
            """Show the window for the first time, in its requested state."""
            if window.fullscreen:
                cmd = _SW_SHOWNORMAL if window.focus else _SW_SHOWNOACTIVATE
            elif window.maximized:
                cmd = _SW_SHOWMAXIMIZED
            elif window.minimized:
                cmd = _SW_SHOWMINIMIZED if window.focus else _SW_SHOWMINNOACTIVE
            else:
                cmd = _SW_SHOWNORMAL if window.focus else _SW_SHOWNOACTIVATE

            if window.hidden:
                # The requested state applies once the window is shown.
                self._initial_show_cmd = cmd
                return

            _ShowWindow(self.hwnd, cmd)
            self.update_webview_visibility()

        @invoke_on_ui_thread
        def set_title(self, title: str):
            _SetWindowTextW(self.hwnd, title)

        @invoke_on_ui_thread
        def clear_cookies(self):
            if self.browser is not None:
                self.browser.clear_cookies()

        @invoke_on_ui_thread
        def get_cookies(self, cookies: list[SimpleCookie], semaphore: Semaphore):
            if self.browser is None:
                semaphore.release()
                return
            self.browser.get_cookies(cookies, semaphore)

        @invoke_on_ui_thread
        def load_html(self, content: str, base_uri: str):
            if self.browser is not None:
                self.browser.load_html(content, base_uri)

        @invoke_on_ui_thread
        def load_url(self, url: str):
            if self.browser is not None:
                self.browser.load_url(url)

        @invoke_on_ui_thread
        def hide(self):
            _ShowWindow(self.hwnd, _SW_HIDE)
            self.update_webview_visibility()

        @invoke_on_ui_thread
        def show(self):
            cmd = self._initial_show_cmd
            self._initial_show_cmd = None

            if cmd is None:
                cmd = _SW_SHOW if self.pywebview_window.focus else _SW_SHOWNA

            _ShowWindow(self.hwnd, cmd)
            if self.pywebview_window.focus:
                _SetForegroundWindow(self.hwnd)
            self.update_webview_visibility()

        def is_active(self) -> bool:
            return self._is_active

        @invoke_on_ui_thread
        def set_window_menu(self, menu_list: Iterable[Menu]):
            if self.pywebview_window.transparent:
                # A menu bar is painted into the surface a transparent window
                # does without, so it would take clicks without being seen.
                logger.warning('The win32 backend shows no menu bar on a transparent window.')
                return

            actions: dict[int, MenuAction] = {}

            def append_items(hmenu: int, items: Iterable[Menu | MenuAction | MenuSeparator]):
                for item in items:
                    if isinstance(item, MenuSeparator):
                        _AppendMenuW(hmenu, _MF_SEPARATOR, 0, None)
                    elif isinstance(item, MenuAction):
                        command_id = len(actions) + 1
                        actions[command_id] = item
                        _AppendMenuW(hmenu, _MF_STRING, command_id, item.title)
                    elif isinstance(item, Menu):
                        submenu = _CreatePopupMenu()
                        append_items(submenu, item.items)
                        _AppendMenuW(hmenu, _MF_POPUP, submenu, item.title)

            bar = _CreateMenu()
            has_items = False

            for menu in menu_list:
                # '__app__' is a macOS-only menu container.
                if isinstance(menu, Menu) and menu.title == '__app__':
                    continue
                append_items(bar, [menu])
                has_items = True

            if not has_items:
                _DestroyMenu(bar)
                bar = None

            if self._fullscreen_restore is not None:
                # The bar comes back when fullscreen ends.
                style, placement, old = self._fullscreen_restore
                self._fullscreen_restore = (style, placement, bar or 0)
            else:
                old = _GetMenu(self.hwnd)
                _SetMenu(self.hwnd, bar)
                _DrawMenuBar(self.hwnd)

            if old:
                _DestroyMenu(old)

            self._menu_actions = actions

        @invoke_on_ui_thread
        def toggle_fullscreen(self):
            if self._fullscreen_restore is None:
                style = _GetWindowLongPtrW(self.hwnd, _GWL_STYLE)
                placement = _WINDOWPLACEMENT()
                placement.length = ctypes.sizeof(_WINDOWPLACEMENT)
                _GetWindowPlacement(self.hwnd, ctypes.byref(placement))
                menu = _GetMenu(self.hwnd) or 0

                monitor = _MonitorFromWindow(self.hwnd, _MONITOR_DEFAULTTONEAREST)
                bounds = _monitor_info(monitor).rcMonitor

                self._fullscreen_restore = (style, placement, menu)
                if menu:
                    _SetMenu(self.hwnd, None)
                _SetWindowLongPtrW(self.hwnd, _GWL_STYLE, style & ~_WS_OVERLAPPEDWINDOW)
                flags = _SWP_NOOWNERZORDER | _SWP_FRAMECHANGED
                if not self.pywebview_window.focus:
                    flags |= _SWP_NOACTIVATE
                _SetWindowPos(
                    self.hwnd,
                    _HWND_TOP,
                    bounds.left,
                    bounds.top,
                    bounds.right - bounds.left,
                    bounds.bottom - bounds.top,
                    flags,
                )
            else:
                style, placement, menu = self._fullscreen_restore
                self._fullscreen_restore = None

                _SetWindowLongPtrW(self.hwnd, _GWL_STYLE, style)
                if menu:
                    _SetMenu(self.hwnd, menu)
                # The saved placement's show command would show a hidden
                # window, and activate a window that must not take focus.
                if not _IsWindowVisible(self.hwnd):
                    placement.showCmd = _SW_HIDE
                elif not self.pywebview_window.focus and placement.showCmd == _SW_SHOWNORMAL:
                    placement.showCmd = _SW_SHOWNOACTIVATE
                _SetWindowPlacement(self.hwnd, ctypes.byref(placement))
                _SetWindowPos(
                    self.hwnd,
                    None,
                    0,
                    0,
                    0,
                    0,
                    _SWP_NOMOVE
                    | _SWP_NOSIZE
                    | _SWP_NOZORDER
                    | _SWP_NOOWNERZORDER
                    | _SWP_FRAMECHANGED,
                )

        @invoke_on_ui_thread
        def set_on_top(self, on_top: bool):
            _SetWindowPos(
                self.hwnd,
                _HWND_TOPMOST if on_top else _HWND_NOTOPMOST,
                0,
                0,
                0,
                0,
                _SWP_NOMOVE | _SWP_NOSIZE | _SWP_NOACTIVATE,
            )

        @invoke_on_ui_thread
        def get_size(self):
            scale = self._scale
            rect = wintypes.RECT()
            _GetWindowRect(self.hwnd, ctypes.byref(rect))
            return (int((rect.right - rect.left) / scale), int((rect.bottom - rect.top) / scale))

        @invoke_on_ui_thread
        def resize(self, width: int, height: int, fix_point: FixPoint):
            scale = self._scale
            physical_width = int(width * scale)
            physical_height = int(height * scale)
            rect = wintypes.RECT()
            _GetWindowRect(self.hwnd, ctypes.byref(rect))
            x, y = rect.left, rect.top

            if fix_point & FixPoint.EAST:
                x += rect.right - rect.left - physical_width

            if fix_point & FixPoint.SOUTH:
                y += rect.bottom - rect.top - physical_height

            _SetWindowPos(
                self.hwnd,
                None,
                x,
                y,
                physical_width,
                physical_height,
                _SWP_NOZORDER | _SWP_NOACTIVATE,
            )

        @invoke_on_ui_thread
        def get_position(self):
            # A desktop-wide coordinate: the primary monitor's scale, as in
            # get_screens(), so this round-trips with move().
            scale = _primary_monitor_scale()
            rect = wintypes.RECT()
            _GetWindowRect(self.hwnd, ctypes.byref(rect))
            return (int(rect.left / scale), int(rect.top / scale))

        @invoke_on_ui_thread
        def move(self, x: int, y: int):
            scale = _primary_monitor_scale()
            _SetWindowPos(
                self.hwnd,
                None,
                int(x * scale),
                int(y * scale),
                0,
                0,
                _SWP_NOSIZE | _SWP_NOZORDER | _SWP_NOACTIVATE,
            )

        def _change_state(self, visible_cmd: int, hidden_cmd: int) -> None:
            """
            Apply a window state now, or, for a hidden window, when show()
            shows it: every ShowWindow command but SW_HIDE makes it visible.
            """
            if _IsWindowVisible(self.hwnd):
                _ShowWindow(self.hwnd, visible_cmd)
                self.update_webview_visibility()
            else:
                self._initial_show_cmd = hidden_cmd

        @invoke_on_ui_thread
        def maximize(self):
            self._change_state(_SW_SHOWMAXIMIZED, _SW_SHOWMAXIMIZED)

        @invoke_on_ui_thread
        def minimize(self):
            self._change_state(_SW_MINIMIZE, _SW_SHOWMINNOACTIVE)

        @invoke_on_ui_thread
        def restore(self):
            focus = self.pywebview_window.focus
            self._change_state(_SW_RESTORE, _SW_SHOWNORMAL if focus else _SW_SHOWNOACTIVATE)

        @invoke_on_ui_thread
        def close(self):
            # DestroyWindow() sends no WM_CLOSE, so route through
            # _begin_close() to fire the `closing` event and confirm_close prompt.
            if not self.destroyed and self._begin_close():
                _DestroyWindow(self.hwnd)


# ── Application lifetime ─────────────────────────────────────────────────────

_main_window_created = Event()
# Why child windows cannot be created: set when the master window fails or
# closes before its WebView2 is ready.
_main_window_creation_error: BaseException | None = None
# Why webview.start() fails: set only for a real failure, not for a master
# window the user closed early, after which start() returns as on WinForms.
_start_error: BaseException | None = None
# False once the message loop has ended, so no window outlives it.
_accepting_windows = False
_private_cleanup_thread: threading.Thread | None = None
_app_setup = False


def _async_creation_error(component: str, operation, status: AsyncStatus) -> RuntimeError:
    if status == AsyncStatus.ERROR:
        return RuntimeError(f'Error creating {component}: {WinError(operation.error_code)}')
    return RuntimeError(f'Creating {component} was canceled')


def _fail_main_window_creation(error: BaseException, *, closed_early: bool = False) -> None:
    """
    Release the threads waiting to create child windows. For a real failure,
    also make webview.start() raise and end the message loop; a master
    window closed early is already on its way out. UI thread only.
    """
    global _main_window_creation_error, _start_error

    _main_window_creation_error = error
    _main_window_created.set()

    if closed_early:
        return

    _start_error = error
    _destroy_all_windows()


def _destroy_all_windows() -> None:
    """Destroy every window, skipping `closing` and confirm_close. UI thread only."""
    forms = list(BrowserView.instances.values())
    if not forms:
        _PostQuitMessage(0)

    for form in forms:
        if not form.destroyed:
            _DestroyWindow(form.hwnd)


@_HANDLER_ROUTINE
def _console_ctrl_handler(ctrl_type: int) -> bool:
    """
    Ctrl+C in the console closes every window, as on WinForms. Windows calls
    this on a thread of its own, so the work goes to the UI thread's queue;
    returning True keeps Python from raising KeyboardInterrupt in the middle
    of a window procedure.
    """
    if ctrl_type != _CTRL_C_EVENT:
        return False
    return _enqueue(_destroy_all_windows)


def _fail_child_window_creation(form: BrowserView.BrowserForm) -> None:
    """
    Close a secondary window whose WebView2 failed to start. Unlike the
    master window's failure, this leaves the application running. It skips
    the `closing` event and `confirm_close`: a window that failed to start is
    always torn down.
    """
    if not form.destroyed:
        with contextlib.suppress(Exception):
            _DestroyWindow(form.hwnd)


def _wait_for_main_window() -> None:
    _main_window_created.wait()
    if _main_window_creation_error is not None:
        raise RuntimeError('Main window creation failed') from _main_window_creation_error


def _run_message_loop() -> None:
    msg = wintypes.MSG()
    while True:
        result = _GetMessageW(ctypes.byref(msg), None, 0, 0)
        if result == 0:
            return
        if result == -1:
            raise WinError(ctypes.get_last_error())
        _TranslateMessage(ctypes.byref(msg))
        _DispatchMessageW(ctypes.byref(msg))


def _teardown_app() -> None:
    """
    Shut the DispatcherQueue down, running what is still queued, then leave
    the apartment, so that the next webview.start() begins afresh.
    """
    global _app_setup, _dispatcher_controller, _dispatcher_queue, _compositor

    msg = wintypes.MSG()

    # Windows still open here were never closed, e.g. after an exception
    # escaped the loop; they would otherwise stay on screen, unresponsive.
    _destroy_all_windows()

    # The Compositor belongs to the DispatcherQueue shut down below.
    if _compositor is not None:
        _compositor.close()
        _compositor = None

    controller = _dispatcher_controller
    if controller is not None:
        done = Event()
        thread_id = _ui_thread_id

        def on_shutdown(op: IAsyncAction, status: AsyncStatus) -> None:
            done.set()
            # Wake GetMessageW below, whichever thread this runs on.
            _PostThreadMessageW(thread_id, _WM_NULL, 0, 0)

        controller.shutdown_queue_async().completed = on_shutdown
        controller = None

        while not done.is_set():
            result = _GetMessageW(ctypes.byref(msg), None, 0, 0)
            if result == -1:
                break
            if result == 0:
                # A WM_QUIT left over from closing the windows.
                continue
            _TranslateMessage(ctypes.byref(msg))
            _DispatchMessageW(ctypes.byref(msg))

    # A WM_QUIT posted by a window destroyed above would end the next
    # webview.start()'s loop the moment it began.
    while _PeekMessageW(ctypes.byref(msg), None, _WM_QUIT, _WM_QUIT, _PM_REMOVE):
        pass

    _dispatcher_controller = None
    _dispatcher_queue = None
    _forms_by_hwnd.clear()
    _app_setup = False
    uninit_apartment()


def init_storage():
    global cache_dir

    if not _state['private_mode'] or _state['storage_path']:
        try:
            try:
                # Only succeeds if the current process has package identity.
                data_folder = ApplicationData.current.local_folder.path
            except OSError:
                data_folder = os.environ.get('APPDATA') or os.path.expanduser('~')

            cache_dir = _state['storage_path'] or os.path.join(data_folder, 'pywebview')

            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir)
        except Exception as ex:
            logger.exception(f'Cache directory creation failed: {ex}')
    else:
        _cache_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        atexit.register(_cache_dir.cleanup)
        cache_dir = _cache_dir.name


def setup_app():
    # MUST be called before create_window and set_app_menu
    global _app_setup, _dispatcher_controller, _dispatcher_queue, _ui_thread_id
    global _main_window_creation_error, _start_error

    if _app_setup:
        return

    _main_window_created.clear()
    _main_window_creation_error = None
    _start_error = None

    _set_dpi_awareness()

    init_apartment(ApartmentType.SINGLE_THREADED)
    try:
        # A DispatcherQueue on this thread, which the message loop pumps, is
        # how other threads get work onto the UI thread.
        _dispatcher_controller = create_dispatcher_queue_controller(
            DispatcherQueueThreadType.CURRENT, DispatcherQueueThreadApartmentType.NONE
        )
        _dispatcher_queue = _dispatcher_controller.dispatcher_queue
        _ui_thread_id = _GetCurrentThreadId()
        _register_window_class()
    except BaseException:
        _dispatcher_controller = None
        _dispatcher_queue = None
        uninit_apartment()
        raise

    _app_setup = True


def create_window(window: _Window):
    def create() -> None:
        if not _accepting_windows:
            raise RuntimeError('The application is shutting down')

        # Empty only if init_storage() failed, which leaves WebView2 its default folder.
        browser = BrowserView.BrowserForm(window, cache_dir or '')
        BrowserView.instances[window.uid] = browser
        window.events.before_show.set()
        browser.show_initial(window)

        if not window.events.shown.is_set():
            window.events.shown.set()

    if window.uid == 'master':
        global _private_cleanup_thread, _accepting_windows

        init_storage()
        _accepting_windows = True
        _SetConsoleCtrlHandler(_console_ctrl_handler, True)

        try:
            try:
                create()
            except BaseException as error:
                # Ends the message loop below once any window is gone.
                logger.exception('Failed to create the main window')
                _fail_main_window_creation(error)

            _run_message_loop()
        finally:
            _accepting_windows = False
            _SetConsoleCtrlHandler(_console_ctrl_handler, False)
            _teardown_app()
            BrowserView.instances.clear()
            if _private_cleanup_thread is not None:
                # The browser process must exit before private-mode data can
                # be removed; the caller's script resumes only after that.
                _private_cleanup_thread.join()
                _private_cleanup_thread = None

        if _start_error is not None:
            raise RuntimeError('Main window creation failed') from _start_error
    else:
        _wait_for_main_window()

        def create_guarded() -> None:
            try:
                create()
            except BaseException as error:
                # A secondary window that failed to construct must still
                # release whoever waits on its events.
                logger.error('Failed to create window %r: %s', window.uid, error)
                browser = BrowserView.instances.get(window.uid)
                if browser is not None:
                    _fail_child_window_creation(browser)
                else:
                    if window in windows:
                        windows.remove(window)
                    # A window destroyed during construction already fired it.
                    if not window.events.closed.is_set():
                        window.events.closed.set()
                window.events.before_show.set()
                window.events.shown.set()

        if not _enqueue(create_guarded):
            raise RuntimeError('Failed to enqueue callback')


def set_title(title: str, uid: str):
    i = BrowserView.instances.get(uid)
    if i:
        i.set_title(title)


def create_confirmation_dialog(title: str, message: str, uid: str) -> bool | None:
    i = BrowserView.instances.get(uid)
    if not i:
        return None

    fut = Future[bool]()

    def callback():
        _show_message_dialog(
            i.hwnd,
            message,
            title,
            [i.localization['global.ok'], i.localization['global.cancel']],
            lambda index: fut.set_result(index == 0),
        )

    return _run_dispatched(callback, fut)


def _folder_dialog_callback(
    handle: int, allow_multiple: bool, directory: str, fut: 'Future[tuple[str, ...] | None]'
):
    def callback():
        if allow_multiple or directory or _pickers_unavailable():
            # FolderPicker has neither multi-select nor an initial directory;
            # IFileOpenDialog (Win32 COM) has both.
            folders = pick_folders_win32(handle, allow_multiple=allow_multiple, directory=directory)
            fut.set_result(tuple(folders) if folders is not None else None)
            return

        picker = FolderPicker()
        initialize_with_window(picker, handle)
        picker.suggested_start_location = PickerLocationId.DOWNLOADS
        picker.file_type_filter.append('*')

        op = picker.pick_single_folder_async()

        def on_completed(op: IAsyncOperation[StorageFolder], status: AsyncStatus):
            if status == AsyncStatus.ERROR:
                fut.set_exception(WinError(op.error_code))
            elif status == AsyncStatus.CANCELED:
                fut.set_result(None)
            elif status == AsyncStatus.COMPLETED:
                result = op.get_results()
                fut.set_result((result.path,) if result else None)

        op.completed = on_completed

    return callback


def _open_dialog_callback(
    handle: int,
    allow_multiple: bool,
    file_types: list[str],
    directory: str,
    fut: 'Future[tuple[str, ...] | None]',
):
    def callback():
        if directory or _pickers_unavailable():
            # FileOpenPicker has no initial directory; IFileOpenDialog has.
            files = pick_files_win32(handle, allow_multiple, file_types, directory)
            fut.set_result(tuple(files) if files is not None else None)
            return

        picker = FileOpenPicker()
        initialize_with_window(picker, handle)
        picker.suggested_start_location = PickerLocationId.DOWNLOADS

        if file_types:
            parsed_exts: list[str] = []
            for _, exts in [parse_file_type(f) for f in file_types]:
                for ext in exts.split(';'):
                    stripped = ext[1:]  # '*.jpg' → '.jpg'; '*.*'/'*' → '.*'/''
                    if not stripped or '*' in stripped:
                        parsed_exts = ['*']  # any wildcard → allow all
                        break
                    parsed_exts.append(stripped)
                if parsed_exts == ['*']:
                    break
            for ext in parsed_exts:
                picker.file_type_filter.append(ext)
        else:
            picker.file_type_filter.append('*')

        if allow_multiple:
            op = picker.pick_multiple_files_async()

            def on_multiple_completed(
                op: IAsyncOperation[Sequence[StorageFile]], status: AsyncStatus
            ):
                if status == AsyncStatus.ERROR:
                    fut.set_exception(WinError(op.error_code))
                elif status == AsyncStatus.CANCELED:
                    fut.set_result(None)
                elif status == AsyncStatus.COMPLETED:
                    result = op.get_results()
                    fut.set_result(tuple(f.path for f in result) if result else None)

            op.completed = on_multiple_completed
        else:
            single_op = picker.pick_single_file_async()

            def on_completed(op: IAsyncOperation[StorageFile | None], status: AsyncStatus):
                if status == AsyncStatus.ERROR:
                    fut.set_exception(WinError(op.error_code))
                elif status == AsyncStatus.CANCELED:
                    fut.set_result(None)
                elif status == AsyncStatus.COMPLETED:
                    result = op.get_results()
                    fut.set_result((result.path,) if result else None)

            single_op.completed = on_completed

    return callback


def _save_dialog_callback(
    handle: int,
    uid: str,
    save_filename: str,
    file_types: list[str],
    directory: str,
    fut: 'Future[tuple[str, ...] | None]',
):
    def callback():
        if directory or _pickers_unavailable():
            # FileSavePicker has no initial directory; IFileSaveDialog has.
            path = pick_save_file_win32(handle, save_filename, file_types, directory)
            fut.set_result((path,) if path else None)
            return

        picker = FileSavePicker()
        initialize_with_window(picker, handle)
        picker.suggested_start_location = PickerLocationId.DOWNLOADS
        picker.settings_identifier = uid
        picker.suggested_file_name = save_filename

        if file_types:
            for description, patterns in map(parse_file_type, file_types):
                extensions = []
                for pattern in patterns.split(';'):
                    extension = pattern[1:]  # '*.jpg' → '.jpg'
                    if not extension or '*' in extension:
                        extensions = ['.']
                        break
                    extensions.append(extension)
                picker.file_type_choices[description] = extensions
        else:
            # FileSavePicker takes no wildcard type; '.' with a label stands in.
            picker.file_type_choices['*'] = ['.']

        op = picker.pick_save_file_async()

        def on_completed(op: IAsyncOperation[StorageFile | None], status: AsyncStatus):
            if status == AsyncStatus.ERROR:
                fut.set_exception(WinError(op.error_code))
            elif status == AsyncStatus.CANCELED:
                fut.set_result(None)
            elif status == AsyncStatus.COMPLETED:
                result = op.get_results()
                fut.set_result((result.path,) if result else None)

        op.completed = on_completed

    return callback


def create_file_dialog(
    dialog_type: int,
    directory: str,
    allow_multiple: bool,
    save_filename: str,
    file_types: list[str],
    uid: str,
) -> tuple[str, ...] | None:
    i = BrowserView.instances.get(uid)
    if not i:
        return None

    # The WinRT pickers cannot start in a given directory
    # (https://github.com/microsoft/WindowsAppSDK/issues/88) and fail in an
    # elevated process, so then the callbacks use the Win32 IFileDialog,
    # which pumps its own modal loop and so completes synchronously.
    fut: Future[tuple[str, ...] | None] = Future()
    win32_dialog = bool(directory) or _pickers_unavailable()

    if dialog_type == FileDialog.FOLDER:
        callback = _folder_dialog_callback(i.hwnd, allow_multiple, directory, fut)
        may_complete_synchronously = allow_multiple or win32_dialog
    elif dialog_type == FileDialog.OPEN:
        callback = _open_dialog_callback(i.hwnd, allow_multiple, file_types, directory, fut)
        may_complete_synchronously = win32_dialog
    elif dialog_type == FileDialog.SAVE:
        callback = _save_dialog_callback(i.hwnd, uid, save_filename, file_types, directory, fut)
        may_complete_synchronously = win32_dialog
    else:
        raise ValueError('Invalid dialog type')

    return _run_dispatched(callback, fut, may_complete_synchronously)


def clear_cookies(uid: str):
    i = BrowserView.instances.get(uid)
    if i:
        i.clear_cookies()


def get_cookies(uid: str):
    i = BrowserView.instances.get(uid)
    if not i:
        return

    if _has_ui_thread_access():
        # The lookup's result is delivered through this thread's dispatcher,
        # which waiting here would block.
        raise RuntimeError(
            'get_cookies() cannot be awaited synchronously from the UI thread without '
            'deadlocking the dispatcher that must deliver the result.'
        )

    semaphore = Semaphore(0)
    cookies: list[SimpleCookie] = []

    i.get_cookies(cookies, semaphore)

    semaphore.acquire()

    return cookies


def get_current_url(uid: str):
    i = BrowserView.instances.get(uid)
    if i and i.browser:
        return i.browser.url


def load_url(url: str, uid: str):
    i = BrowserView.instances.get(uid)
    if i:
        i.load_url(url)


def load_html(content: str, base_uri: str, uid: str):
    i = BrowserView.instances.get(uid)
    if i:
        i.load_html(content, base_uri)


def set_app_menu(app_menu_list: Iterable[Menu]):
    BrowserView.app_menu_list = app_menu_list


def get_active_window():
    for i in BrowserView.instances.values():
        if i.is_active():
            return i.pywebview_window

    return None


def show(uid: str):
    i = BrowserView.instances.get(uid)
    if i:
        i.show()


def hide(uid: str):
    i = BrowserView.instances.get(uid)
    if i:
        i.hide()


def toggle_fullscreen(uid: str):
    i = BrowserView.instances.get(uid)
    if i:
        i.toggle_fullscreen()


def set_on_top(uid: str, on_top: bool):
    i = BrowserView.instances.get(uid)
    if i:
        i.set_on_top(on_top)


def resize(width: int, height: int, uid: str, fix_point: FixPoint):
    i = BrowserView.instances.get(uid)
    if i:
        i.resize(width, height, fix_point)


def move(x: int, y: int, uid: str):
    i = BrowserView.instances.get(uid)
    if i:
        i.move(x, y)


def maximize(uid: str):
    i = BrowserView.instances.get(uid)
    if i:
        i.maximize()


def minimize(uid: str):
    i = BrowserView.instances.get(uid)
    if i:
        i.minimize()


def restore(uid: str):
    i = BrowserView.instances.get(uid)
    if i:
        i.restore()


def destroy_window(uid: str):
    i = BrowserView.instances.get(uid)
    if i:
        i.close()


def evaluate_js(script: str, uid: str, parse_json: bool = True):
    i = BrowserView.instances.get(uid)
    if i:
        return i.evaluate_js(script, parse_json)


def get_position(uid: str):
    i = BrowserView.instances.get(uid)
    if i:
        return i.get_position()


def get_size(uid: str):
    i = BrowserView.instances.get(uid)
    if i:
        return i.get_size()


def get_screens():
    """Get all screens with coordinates in logical pixels."""
    monitors: list[int] = []

    @_MONITORENUMPROC
    def on_monitor(monitor, hdc, rect, lparam):
        monitors.append(monitor)
        return True

    _EnumDisplayMonitors(None, None, on_monitor, 0)

    infos = [(monitor, _monitor_info(monitor)) for monitor in monitors]
    # webview.screens documents the primary display as the first element.
    infos.sort(key=lambda item: not item[1].dwFlags & _MONITORINFOF_PRIMARY)

    # Monitor rectangles are physical pixels. Converting every screen's whole
    # rectangle through the primary monitor's scale keeps adjacent monitors
    # adjacent for any mixed-DPI layout; each monitor's own scale is still
    # reported in Screen.scale.
    primary_scale = _primary_monitor_scale()

    screens = []
    for monitor, info in infos:
        bounds = info.rcMonitor
        screens.append(
            Screen(
                int(bounds.left / primary_scale),
                int(bounds.top / primary_scale),
                int((bounds.right - bounds.left) / primary_scale),
                int((bounds.bottom - bounds.top) / primary_scale),
                monitor,
                _monitor_scale(monitor),
                origin_scale=primary_scale,
            )
        )

    return screens


def add_tls_cert(_):
    return
