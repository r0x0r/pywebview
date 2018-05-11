# -*- coding: utf-8 -*-

"""
(C) 2014-2018 Roman Sirokov and contributors
Licensed under BSD license

http://github.com/r0x0r/pywebview/
"""
from __future__ import absolute_import

# disable logging for comtypes
import logging
logging.getLogger("comtypes.client._generate").disabled = True
logging.getLogger("comtypes.client._code_cache").disabled = True

import win32con, win32api, win32gui
from win32com.shell import shell, shellcon
import os
import sys

from ctypes import byref, POINTER
from comtypes import COMObject, hresult
from comtypes.client import wrap, GetEvents

from webview.win32_gen import *
from webview.win32_shared import set_ie_mode
from webview.localization import localization
from webview import OPEN_DIALOG, FOLDER_DIALOG, SAVE_DIALOG

logger = logging.getLogger(__name__)

"""

HERE BE DRAGONS

"""

_user32 = windll.user32
_atl = windll.atl

# for some reason we have to set an offset for the height of ATL window in order for the vertical scrollbar to be fully
# visible
VERTICAL_SCROLLBAR_OFFSET = 20
NON_RESIZEABLE_OFFSET = 6


class UIHandler(COMObject):
    _com_interfaces_ = [IDocHostUIHandler]

    def __init__(self, *args, **kwargs):
        COMObject.__init__(self, *args, **kwargs)

    def ShowContextMenu(self, *args, **kwarg):
        # Disable context menu
        return False

    def GetHostInfo(self, doc):
        doc.contents.dwFlags |= 0x40000000
        return hresult.S_OK


class BrowserView(object):
    instance = None

    def __init__(self, title, url, width, height, resizable, fullscreen, min_size, webview_ready):
        BrowserView.instance = self
        self.title = title
        self.width = width
        self.height = height
        self.url = url
        self.resizable = resizable
        self.fullscreen = fullscreen
        self.min_size = min_size
        self.webview_ready = webview_ready

        self.scrollbar_width = win32api.GetSystemMetrics(win32con.SM_CXVSCROLL)
        self.scrollbar_height = win32api.GetSystemMetrics(win32con.SM_CYHSCROLL)

        self.atlhwnd = -1  # AtlAx host window hwnd
        self.browser = None  # IWebBrowser2 COM object

        self._register_window()
        # In order for system events (most notably WM_DESTROY for application quite) propagate correctly, we need to
        # create two windows: AtAlxWin inside MyWin. AtlAxWin hosts the MSHTML ActiveX control and MainWin receives
        # system messages.
        self._create_main_window()
        self._create_atlax_window()

    def _register_window(self):
        message_map = {
            win32con.WM_DESTROY: self._on_destroy,
            win32con.WM_SIZE: self._on_resize,
            win32con.WM_ERASEBKGND: self._on_erase_bkgnd,
            win32con.WM_GETMINMAXINFO: self._on_minmax_info
        }

        self.wndclass = win32gui.WNDCLASS()
        self.wndclass.style = win32con.CS_HREDRAW | win32con.CS_VREDRAW
        self.wndclass.lpfnWndProc = message_map
        self.wndclass.hInstance = win32api.GetModuleHandle()
        self.wndclass.hCursor = win32gui.LoadCursor(win32con.NULL, win32con.IDC_ARROW)
        self.wndclass.hbrBackground = win32gui.GetStockObject(win32con.WHITE_BRUSH)
        self.wndclass.lpszMenuName = ""
        self.wndclass.lpszClassName = "MainWin"

        try:  # Try loading an icon embedded in the exe file. This will crash when frozen with PyInstaller
            self.wndclass.hIcon = win32gui.LoadIcon(self.wndclass.hInstance, 1)
        except:
            pass

        # Register Window Class
        if not win32gui.RegisterClass(self.wndclass):
            raise WinError()

    def _create_main_window(self):
        # Set window style
        style = win32con.WS_VISIBLE | win32con.WS_OVERLAPPEDWINDOW
        if not self.resizable:
            style = style ^ win32con.WS_THICKFRAME

        #  Center window on the screen
        screen_x = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        screen_y = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
        self.pos_x = int((screen_x - self.width) / 2)
        self.pos_y = int((screen_y - self.height) / 2)

        # Create Window
        self.hwnd = win32gui.CreateWindow(self.wndclass.lpszClassName,
                                          self.title, style, self.pos_x, self.pos_y, self.width, self.height,
                                          None, None, self.wndclass.hInstance, None)

        # Set fullscreen
        if self.fullscreen:
            self.width = screen_x
            self.height = screen_y

            style = win32gui.GetWindowLong(self.hwnd, win32con.GWL_STYLE)
            win32gui.SetWindowLong(self.hwnd, win32con.GWL_STYLE, style & ~(win32con.WS_CAPTION | win32con.WS_THICKFRAME))

            win32gui.SetWindowLong(self.hwnd, win32con.GWL_EXSTYLE, style &
                                   ~(win32con.WS_EX_DLGMODALFRAME | win32con.WS_EX_WINDOWEDGE |
                                     win32con.WS_EX_CLIENTEDGE | win32con.WS_EX_STATICEDGE))

            win32gui.SetWindowPos(self.hwnd, win32con.HWND_TOP, 0, 0, screen_x, screen_y,
                                  win32con.SWP_NOOWNERZORDER | win32con.SWP_FRAMECHANGED | win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE)
        else:
            win32gui.SetWindowPos(self.hwnd, win32con.HWND_TOP, self.pos_x, self.pos_y, self.width, self.height,
                                  win32con.SWP_SHOWWINDOW)


    def _create_atlax_window(self):
        _atl.AtlAxWinInit()
        hInstance = win32api.GetModuleHandle(None)

        if self.fullscreen:
            atl_width = self.width
            atl_height = self.height
        elif not self.resizable:
            atl_width = self.width - NON_RESIZEABLE_OFFSET
            atl_height = self.height - self.scrollbar_height - NON_RESIZEABLE_OFFSET * 2
        else:
            atl_width = self.width - self.scrollbar_width
            atl_height = self.height - self.scrollbar_height - VERTICAL_SCROLLBAR_OFFSET

        self.atlhwnd = win32gui.CreateWindow("AtlAxWin", "about:blank",
                                             win32con.WS_CHILD | win32con.WS_HSCROLL | win32con.WS_VSCROLL,
                                             0, 0, atl_width, atl_height, self.hwnd, None, hInstance, None)

        # COM voodoo
        pBrowserUnk = POINTER(IUnknown)()
        _atl.AtlAxGetControl(self.atlhwnd, byref(pBrowserUnk))
        self.browser = wrap(pBrowserUnk)
        self.browser.RegisterAsBrowser = True
        self.browser.AddRef()
        self.conn = GetEvents(self.browser, sink=self)

    def show(self):
        # Show main window
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOWNORMAL)
        win32gui.UpdateWindow(self.hwnd)

        # Show AtlAx window
        win32gui.ShowWindow(self.atlhwnd, win32con.SW_SHOW)
        win32gui.UpdateWindow(self.atlhwnd)
        win32gui.SetFocus(self.atlhwnd)

        # Load URL here instead in CreateWindow to prevent a dead-lock
        if self.url:
            self.browser.Navigate2(self.url)

        # Start sending and receiving messages
        win32gui.PumpMessages()

    def destroy(self):
        win32gui.SendMessage(self.hwnd, win32con.WM_DESTROY)

    def load_url(self, url):
        self.url = url
        self.browser.Navigate2(url)

    def get_current_url(self):
        raise NotImplementedError("get_current_url not implemented for Win32. Use Windows Forms implementation")

    def load_html(self, content):
        raise NotImplementedError("load_html not implemented for Win32. Use Windows Forms implementation")

    def toggle_fullscreen(self):
        raise NotImplementedError("toggle_fullscreen not implemented for Win32. Use Windows Forms implementation")

    def evaluate_js(self):
        raise NotImplementedError("evaluate_js not implemented for Win32. Use Windows Forms implementation")

    def create_file_dialog(self, dialog_type, directory, allow_multiple, save_filename):
        if not directory:
            directory = os.environ['temp']

        try:
            if dialog_type == FOLDER_DIALOG:
                desktop_pidl = shell.SHGetFolderLocation(0, shellcon.CSIDL_DESKTOP, 0, 0)
                pidl, display_name, image_list =\
                    shell.SHBrowseForFolder(self.hwnd, desktop_pidl, None, 0, None, None)
                file_path = (shell.SHGetPathFromIDList(pidl).decode("utf-8"),)

            elif dialog_type == OPEN_DIALOG:
                file_filter = localization["windows.fileFilter.allFiles"] + u"\0*.*\0"
                custom_filter = localization["windows.fileFilter.otherFiles"] + u"\0*.*\0"

                flags = win32con.OFN_EXPLORER
                if allow_multiple:
                    flags = flags | win32con.OFN_ALLOWMULTISELECT

                file_path, customfilter, flags = \
                    win32gui.GetOpenFileNameW(self.hwnd, InitialDir=directory, Flags=flags, File=None, DefExt="",
                                              Title="", Filter=file_filter, CustomFilter=custom_filter, FilterIndex=0)
                parts = file_path.split('\x00')

                if len(parts) > 1:
                    file_path = tuple([os.path.join(parts[0], file_name) for file_name in parts[1:]])
                else:
                    file_path = (file_path,)

            elif dialog_type == SAVE_DIALOG:
                file_filter = localization["windows.fileFilter.allFiles"] + u"\0*.*\0"
                custom_filter = localization["windows.fileFilter.otherFiles"] + u"\0*.*\0"

                file_path, customfilter, flags = \
                    win32gui.GetSaveFileNameW(self.hwnd, InitialDir=directory, File=save_filename, DefExt="", Title="",
                                              Filter=file_filter, CustomFilter=custom_filter, FilterIndex=0)
        except Exception as e:
            logger.debug("File dialog crash", exc_info=True)
            file_path = None

        return file_path

    def _destroy(self):
        del self.browser
        win32gui.PostQuitMessage(0)

    def _on_destroy(self, hwnd, message, wparam, lparam):
        self._destroy()

        return True

    def _on_resize(self, hwnd, message, wparam, lparam):
        # Resize the ATL window as the size of the main window is changed
        if BrowserView.instance != None and not self.fullscreen:
            atl_hwnd = BrowserView.instance.atlhwnd
            width = win32api.LOWORD(lparam)
            height = win32api.HIWORD(lparam)
            win32gui.SetWindowPos(atl_hwnd, win32con.HWND_TOP, 0, 0, width, height, win32con.SWP_SHOWWINDOW)
            win32gui.ShowWindow(atl_hwnd, win32con.SW_SHOW)
            win32gui.UpdateWindow(atl_hwnd)

        return 0

    def _on_erase_bkgnd(self, hwnd, message, wparam, lparam):
        # Prevent flickering when resizing
        return 0

    def _on_minmax_info(self, hwnd, message, wparam, lparam):
        info = MINMAXINFO.from_address(lparam)
        info.ptMinTrackSize.x = self.min_size[0]
        info.ptMinTrackSize.y = self.min_size[1]

    def DocumentComplete(self, *args):
        if self.browser.Document:
            custom_doc = self.browser.Document.QueryInterface(ICustomDoc)
            self.handler = UIHandler()
            custom_doc.SetUIHandler(self.handler)


def create_window(uid, title, url, width, height, resizable, fullscreen, min_size,
                  confirm_quit, background_color, debug, js_api, webview_ready):
    set_ie_mode()
    browser_view = BrowserView(title, url, width, height, resizable, fullscreen, min_size, webview_ready)
    browser_view.show()


def create_file_dialog(dialog_type, directory, allow_multiple, save_filename, file_types):
    return BrowserView.instance.create_file_dialog(dialog_type, directory, allow_multiple, save_filename)


def get_current_url(uid):
    return BrowserView.instance.get_current_url()


def load_url(url, uid):
    BrowserView.instance.load_url(url)


def load_html(content, base_uri, uid):
    BrowserView.instance.load_html(content)


def destroy_window(uid):
    BrowserView.instance.destroy()


def toggle_fullscreen(uid):
    BrowserView.instance.toggle_fullscreen()


def evaluate_js(script, uid):
    return BrowserView.instance.evaluate_js(script)
