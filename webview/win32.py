# -*- coding: utf-8 -*-

"""
(C) 2014 Roman Sirokov
Licensed under BSD license

http://github.com/r0x0r/pywebview/
"""

import win32con, win32api, win32gui
import sys

from ctypes import *
from ctypes.wintypes import *

from comtypes import IUnknown, STDMETHOD, GUID
from comtypes.client import wrap, GetModule, CreateObject, GetEvents, PumpEvents

"""
#herebedragons
"""

GetModule('shdocvw.dll')

_kernel32 = windll.kernel32
_user32 = windll.user32
_atl = windll.atl


#NULL = c_int(win32con.NULL)
_WNDPROC = WINFUNCTYPE(c_long, c_int, c_uint, c_int, c_int)

class WNDCLASS(Structure):
    _fields_ = [('style', c_uint),
                ('lpfnWndProc', _WNDPROC),
                ('cbClsExtra', c_int),
                ('cbWndExtra', c_int),
                ('hInstance', c_int),
                ('hIcon', c_int),
                ('hCursor', c_int),
                ('hbrBackground', c_int),
                ('lpszMenuName', c_wchar_p),
                ('lpszClassName', c_wchar_p)]

class BrowserView(object):

    class EventSink(object):

        # some DWebBrowserEvents
        def OnVisible(self, this, *args):
            print "OnVisible", args

        def BeforeNavigate(self, this, *args):
            print "BeforeNavigate", args

        def NavigateComplete(self, this, *args):
            print "NavigateComplete", this, args
            return

        def OnQuit(self, this, *args):
            print "OnQuit", args



        # some DWebBrowserEvents2
        def BeforeNavigate2(self, this, *args):
            print "BeforeNavigate2", args

        def NavigateComplete2(self, this, *args):
            print "NavigateComplete2", args

        def WindowStateChanged(self, this, *args):
            print "WindowStateChanged", args

    instance = None

    def WndProc(hwnd, message, wParam, lParam):
        if message == win32con.WM_SIZE:
            # Resize the ATL window as the size of the main window is changed
            if BrowserView.instance != None:
                hwnd = BrowserView.instance.atlhwnd
                width = win32api.LOWORD(lParam)
                height = win32api.HIWORD(lParam)
                _user32.SetWindowPos(hwnd, win32con.HWND_TOP, 0, 0, width, height, win32con.SWP_SHOWWINDOW)
                _user32.ShowWindow(c_int(hwnd), c_int(win32con.SW_SHOW))
                _user32.UpdateWindow(c_int(hwnd))
            return 0

        elif message == win32con.WM_ERASEBKGND:
            # Prevent flickering when resizing
            return 0

        elif message == win32con.WM_CREATE:
            pass #document = BrowserView.instance.browser.Document.QueryInterface(ICustomDoc).SetUIHandler()

        elif message == win32con.WM_DESTROY:
            _user32.PostQuitMessage(0)
            return 0

        return windll.user32.DefWindowProcW(c_int(hwnd), c_int(message), c_int(wParam), c_int(lParam))




    def __init__(self, title, url, width, height, resizable, fullscreen):
        BrowserView.instance = self
        self.title = title
        self.width = width
        self.height = height
        self.url = url
        self.resizable = resizable
        self.fullscreen = fullscreen

        self.atlhwnd = -1  # AtlAx host window hwnd
        self.browser = None  # IWebBrowser2 COM object

        self._register_window()
        # In order for system events (most notably WM_DESTROY for application quite) propagate correctly, we need to
        # create two windows: AtAlxWin inside MyWin. AtlAxWin hosts MSHTML ActiveX control and MainWin receiving
        # system messages.
        self._create_main_window()
        self._create_atlax_window()

    def _register_window(self):
        message_map = {
          win32con.WM_DESTROY: self._on_destroy,
        }

        self.wndclass = win32gui.WNDCLASS()
        self.wndclass.style = win32con.CS_HREDRAW | win32con.CS_VREDRAW
        self.wndclass.lpfnWndProc = message_map
        #self.wndclass.cbClsExtra = self.wndclass.cbWndExtra = 0
        self.wndclass.hInstance = win32api.GetModuleHandle()
        self.wndclass.hCursor = _user32.LoadCursorW(c_int(win32con.NULL), c_int(win32con.IDC_ARROW))
        self.wndclass.hbrBackground = windll.gdi32.GetStockObject(c_int(win32con.WHITE_BRUSH))
        self.wndclass.lpszMenuName = ""
        self.wndclass.lpszClassName = "MainWin"

        # Register Window Class
        if not win32gui.RegisterClass(self.wndclass):
            raise WinError()

    def _create_main_window(self):
        # Set window style
        style = win32con.WS_VISIBLE
        if self.resizable:
            style = style | win32con.WS_OVERLAPPEDWINDOW
        else:
            style = style | (win32con.WS_OVERLAPPEDWINDOW ^ win32con.WS_THICKFRAME)

        #  Center window on the screen
        screen_x = _user32.GetSystemMetrics(win32con.SM_CXSCREEN)
        screen_y = _user32.GetSystemMetrics(win32con.SM_CYSCREEN)
        x = (screen_x - self.width) / 2
        y = (screen_y - self.height) / 2

        # Create Window
        self.hwnd = win32gui.CreateWindow(self.wndclass.lpszClassName,
                                          self.title, style, x, y, self.width, self.height,
                                          None, None, self.wndclass.hInstance, None)

        # Set fullscreen
        if self.fullscreen:
            style = _user32.GetWindowLongW(self.hwnd, win32con.GWL_STYLE)
            _user32.SetWindowLongW(self.hwnd, win32con.GWL_STYLE, style & ~win32con.WS_OVERLAPPEDWINDOW)
            _user32.SetWindowPos(self.hwnd, win32con.HWND_TOP, 0, 0, screen_x, screen_y,
                                 win32con.SWP_NOOWNERZORDER | win32con.SWP_FRAMECHANGED)


    def _create_atlax_window(self):
        _atl.AtlAxWinInit()
        hInstance = win32api.GetModuleHandle(None)
        self.atlhwnd = win32gui.CreateWindow("AtlAxWin", self.url,
                                      win32con.WS_CHILD | win32con.WS_HSCROLL | win32con.WS_VSCROLL,
                                      0, 0, self.width, self.height,
                                      self.hwnd, None, hInstance, None)

        # COM voodoo
        pBrowserUnk = POINTER(IUnknown)()
        _atl.AtlAxGetControl(self.atlhwnd, byref(pBrowserUnk))
        self.browser = wrap(pBrowserUnk)
        self.browser.RegisterAsBrowser = True
        self.browser.AddRef()



    def show(self):
        # Show main window
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOWNORMAL)
        win32gui.UpdateWindow(self.hwnd)

        # Show AtlAx window
        win32gui.ShowWindow(self.atlhwnd, win32con.SW_SHOW)
        win32gui.UpdateWindow(self.atlhwnd)
        win32gui.SetFocus(self.atlhwnd)

        # Pump messages
        win32gui.PumpMessages()


    def load_url(self, url):
        self.url = url
        self.browser.Navigate2(url)

    def _on_destroy(self, hwnd, message, wparam, lparam):
       win32gui.PostQuitMessage(0)

       return True



def create_window(title, url, width, height, resizable, fullscreen):
    set_ie_mode()
    browser_view = BrowserView(title, url, width, height, resizable, fullscreen)
    browser_view.show()



def load_url(url):
    if BrowserView.instance is not None:
        BrowserView.instance.load_url(url)
    else:
        raise Exception("Create a web view window first, before invoking this function")


def set_ie_mode():
    """
    By default hosted IE control emulates IE7 regardless which version of IE is installed. To fix this, a proper value
    must be set for the executable.
    See http://msdn.microsoft.com/en-us/library/ee330730%28v=vs.85%29.aspx#browser_emulation for details on this
    behaviour.
    """

    try:
        import _winreg as winreg  # Python 2
    except ImportError:
        import winreg  # Python 3

    def get_ie_mode():
        """
        Get the installed version of IE
        :return:
        """
        ie_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'Software\Microsoft\Internet Explorer')
        version, type = winreg.QueryValueEx(ie_key, "svcVersion")
        winreg.CloseKey(ie_key)

        if version.startswith("11"):
            value = 0x2AF9
        elif version.startswith("10"):
            value = 0x2711
        elif version.startswith("9"):
            value = 0x270F
        elif version.startswith("8"):
            value = 0x22B8
        else:
            value = 0x2AF9  # Set IE11 as default

        return value

    browser_emulation = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                       r'Software\Microsoft\Internet Explorer\Main\FeatureControl\FEATURE_BROWSER_EMULATION',
                                       0, winreg.KEY_ALL_ACCESS)

    mode = get_ie_mode()
    executable_name = sys.executable.split("\\")[-1]
    winreg.SetValueEx(browser_emulation, executable_name, 0, winreg.REG_DWORD, mode)
    winreg.CloseKey(browser_emulation)

