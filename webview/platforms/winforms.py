import ctypes
import logging
import os
import signal
import sys
import tempfile
import threading
import winreg
from ctypes import windll, wintypes
from platform import machine
from threading import Event, Semaphore

try:
    import clr
except Exception:
    os.environ['PYTHONNET_RUNTIME'] = 'coreclr'
    import clr

from webview import FileDialog, _state, settings, windows
from webview.guilib import forced_gui_
from webview.menu import Menu, MenuAction, MenuSeparator
from webview.platforms import win32
from webview.screen import Screen
from webview.util import inject_base_uri, parse_file_type
from webview.window import FixPoint

clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Collections')
clr.AddReference('System.Threading')
clr.AddReference('System.Reflection')

import System.Windows.Forms as WinForms  # noqa: E402
from Microsoft.Win32 import SystemEvents  # noqa: E402
from System import Array, Environment, Func, Int32, IntPtr, Object, Type, UInt32  # noqa: E402
from System.Drawing import Color, ColorTranslator, Icon, Point, Size, SizeF  # noqa: E402
from System.Reflection import Assembly, BindingFlags  # noqa: E402
from System.Threading import ApartmentState, Thread, ThreadStart  # noqa: E402

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
logger = logging.getLogger('pywebview')
cache_dir = None
_sigint_received = False


def _sigint_handler(signum, frame):
    """
    Handler for SIGINT signal (Ctrl+C).

    Sets a flag that's checked by the timer in the GUI thread. This is necessary because
    the signal handler runs in the main thread, but Application.Exit() must be called
    from the GUI thread. The timer in create_window() checks this flag periodically and
    exits the application when it's set.
    """
    global _sigint_received
    _sigint_received = True


def _is_new_version(current_version: str, new_version: str) -> bool:
    new_range = new_version.split('.')
    cur_range = current_version.split('.')
    for index, _ in enumerate(new_range):
        if len(cur_range) > index:
            return int(new_range[index]) >= int(cur_range[index])

    return False


def _is_chromium():
    if settings['WEBVIEW2_RUNTIME_PATH']:
        return True

    def edge_build(key_type, key, description=''):
        try:
            if machine() == 'x86' or key_type == 'HKEY_CURRENT_USER':
                path = rf'Microsoft\EdgeUpdate\Clients\{key}'
            else:
                path = rf'WOW6432Node\Microsoft\EdgeUpdate\Clients\{key}'

            with winreg.OpenKey(getattr(winreg, key_type), rf'SOFTWARE\{path}') as windows_key:
                build, _ = winreg.QueryValueEx(windows_key, 'pv')
                return str(build)

        except Exception:
            pass

        return '0'

    try:
        net_key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full'
        )
        version, _ = winreg.QueryValueEx(net_key, 'Release')

        if version < 394802:  # .NET 4.6.2
            return False

        build_versions = [
            {
                'key': '{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}',
                'description': 'Microsoft Edge WebView2 Runtime',
            },  # runtime
            {
                'key': '{2CD8A007-E189-409D-A2C8-9AF4EF3C72AA}',
                'description': 'Microsoft Edge WebView2 Beta',
            },  # beta
            {
                'key': '{0D50BFEC-CD6A-4F9A-964C-C7416E3ACB10}',
                'description': 'Microsoft Edge WebView2 Developer',
            },  # dev
            {
                'key': '{65C35B14-6C1D-4122-AC46-7148CC9D6497}',
                'description': 'Microsoft Edge WebView2 Canary',
            },  # canary
        ]

        for item in build_versions:
            for key_type in ('HKEY_CURRENT_USER', 'HKEY_LOCAL_MACHINE'):
                build = edge_build(key_type, item['key'], item['description'])
                if _is_new_version('86.0.622.0', build):  # Webview2 86.0.622.0
                    return True

    except Exception as e:
        logger.exception(e)
    finally:
        winreg.CloseKey(net_key)

    return False


is_cef = forced_gui_ == 'cef'
is_chromium = not is_cef and _is_chromium() and forced_gui_ != 'mshtml'

if is_cef:
    from . import cef as CEF

    IWebBrowserInterop = object

    logger.debug('Using WinForms / CEF')
    renderer = 'cef'
elif is_chromium:
    from . import edgechromium as Chromium

    IWebBrowserInterop = object

    logger.debug('Using WinForms / Chromium')
    renderer = 'edgechromium'
else:
    from . import mshtml as IE

    logger.warning(
        'MSHTML is deprecated. See https://pywebview.flowrl.com/guide/web_engine.html on details how to use Edge Chromium'
    )
    logger.debug('Using WinForms / MSHTML')
    IE._set_ie_mode()
    renderer = 'mshtml'


def DwmSetWindowAttribute(hwnd, attr, value, size=4):
    DwmSetWindowAttribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
    DwmSetWindowAttribute.argtypes = [
        wintypes.HWND,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    return DwmSetWindowAttribute(hwnd, attr, ctypes.byref(ctypes.c_int(value)), size)


def ExtendFrameIntoClientArea(hwnd):
    class _MARGINS(ctypes.Structure):
        _fields_ = [
            ('cxLeftWidth', ctypes.c_int),
            ('cxRightWidth', ctypes.c_int),
            ('cyTopHeight', ctypes.c_int),
            ('cyBottomHeight', ctypes.c_int),
        ]

    DwmExtendFrameIntoClientArea = ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea
    m = _MARGINS()
    m.cxLeftWidth = 1
    m.cxRightWidth = 1
    m.cyTopHeight = 1
    m.cyBottomHeight = 1
    return DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(m))


# --- Frameless resizable window support -------------------------------------
# When a window is frameless (FormBorderStyle = None), WinForms strips
# WS_THICKFRAME from the window style, so the system no longer offers resize
# handles at the edges. To keep ``resizable=True`` working for frameless
# windows we subclass the window procedure and answer ``WM_NCHITTEST``
# ourselves, returning the appropriate edge hit-test code when the cursor is
# near a window border. ``WM_SETCURSOR`` is handled as well so the system
# shows the sizing cursor. WS_THICKFRAME is added back to the style so the
# system resize modal loop engages once it receives the edge hit-test result.

_WM_NCHITTEST = 0x0084
_WM_SETCURSOR = 0x0020
_WM_NCCALCSIZE = 0x0083
_WM_NCACTIVATE = 0x0086
_WM_NCPAINT = 0x0085
_WM_NCUAHDRAWCAPTION = 0x00AE
_WM_NCUAHDRAWFRAME = 0x00AF

_HTCLIENT = 1
_HTLEFT = 10
_HTRIGHT = 11
_HTTOP = 12
_HTTOPLEFT = 13
_HTTOPRIGHT = 14
_HTBOTTOM = 15
_HTBOTTOMLEFT = 16
_HTBOTTOMRIGHT = 17

_IDC_SIZENS = 32645
_IDC_SIZEWE = 32644
_IDC_SIZENWSE = 32642
_IDC_SIZENESW = 32643

_RESIZE_CURSORS = {
    _HTLEFT: _IDC_SIZEWE,
    _HTRIGHT: _IDC_SIZEWE,
    _HTTOP: _IDC_SIZENS,
    _HTBOTTOM: _IDC_SIZENS,
    _HTTOPLEFT: _IDC_SIZENWSE,
    _HTTOPRIGHT: _IDC_SIZENESW,
    _HTBOTTOMLEFT: _IDC_SIZENESW,
    _HTBOTTOMRIGHT: _IDC_SIZENWSE,
}

_GWLP_WNDPROC = -4
_GWL_STYLE = -16
_WS_THICKFRAME = 0x00040000

_WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
)

_GetWindowLongPtrW = windll.user32.GetWindowLongPtrW
_GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
_GetWindowLongPtrW.restype = ctypes.c_void_p
_SetWindowLongPtrW = windll.user32.SetWindowLongPtrW
_SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
_SetWindowLongPtrW.restype = ctypes.c_void_p
_GetWindowLongW = windll.user32.GetWindowLongW
_GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
_GetWindowLongW.restype = ctypes.c_long
_SetWindowLongW = windll.user32.SetWindowLongW
_SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
_SetWindowLongW.restype = ctypes.c_long
_CallWindowProcW = windll.user32.CallWindowProcW
_CallWindowProcW.argtypes = [
    ctypes.c_void_p,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
_CallWindowProcW.restype = ctypes.c_ssize_t


def _get_window_long_ptr(hwnd, index):
    """Get a pointer-sized window attribute, 32/64-bit safe."""
    if ctypes.sizeof(ctypes.c_void_p) == 8:
        return _GetWindowLongPtrW(wintypes.HWND(hwnd), index)
    return _GetWindowLongW(wintypes.HWND(hwnd), index)


def _set_window_long_ptr(hwnd, index, value):
    """Set a pointer-sized window attribute, 32/64-bit safe."""
    if ctypes.sizeof(ctypes.c_void_p) == 8:
        _SetWindowLongPtrW(wintypes.HWND(hwnd), index, ctypes.c_void_p(value))
    else:
        _SetWindowLongW(wintypes.HWND(hwnd), index, ctypes.c_long(value))


class BrowserView:
    instances = {}

    class BrowserForm(WinForms.Form):
        def __init__(self, window, cache_dir):
            super().__init__()
            self.uid = window.uid
            self.pywebview_window = window
            self.pywebview_window.native = self
            self.real_url = None
            self.Text = window.title
            # Store initial window size as logical pixels, will be converted later
            self._initial_width = window.initial_width
            self._initial_height = window.initial_height

            self.AutoScaleDimensions = SizeF(96.0, 96.0)
            self.AutoScaleMode = WinForms.AutoScaleMode.Dpi

            # Always use Manual before Handle is accessed so WinForms never tries
            # to auto-center with the default form size (CenterScreen in
            # OnHandleCreated runs before we set self.Size, so the window gets
            # centered for the wrong dimensions and ends up off-screen).
            self.StartPosition = WinForms.FormStartPosition.Manual

            # Now safe to access Handle / DPI.
            scale = self._scale
            self.Size = Size(int(window.initial_width * scale), int(window.initial_height * scale))
            self.MinimumSize = Size(
                int(window.min_size[0] * scale), int(window.min_size[1] * scale)
            )

            if window.initial_x is not None and window.initial_y is not None:
                # Convert logical pixel coordinates to physical for WinForms
                self.Location = Point(
                    int(window.initial_x * scale),
                    int(window.initial_y * scale),
                )
            elif window.screen:
                # Screen coordinates are in logical pixels, center the window
                # Calculate center position in logical pixels first, then convert to physical
                logical_x = window.screen.x + (window.screen.width - window.initial_width) // 2
                logical_y = window.screen.y + (window.screen.height - window.initial_height) // 2
                self.Location = Point(int(logical_x * scale), int(logical_y * scale))
            else:
                # Size is now correct; CenterToScreen() uses the actual current
                # size and places the window in the middle of the primary screen.
                self.CenterToScreen()

            if not window.resizable:
                self.FormBorderStyle = WinForms.FormBorderStyle.FixedSingle
                self.MaximizeBox = False

            if window.maximized:
                self.WindowState = WinForms.FormWindowState.Maximized
            elif window.minimized:
                self.WindowState = WinForms.FormWindowState.Minimized

            self.old_state = self.WindowState

            # Application icon
            if _state['icon'] and os.path.isfile(_state['icon']):
                self.Icon = Icon(_state['icon'])
            else:
                handle = kernel32.GetModuleHandleW(None)
                icon_handle = windll.shell32.ExtractIconW(handle, sys.executable, 0)

                if icon_handle != 0:
                    self.Icon = Icon.FromHandle(IntPtr.op_Explicit(Int32(icon_handle))).Clone()
                    windll.user32.DestroyIcon(icon_handle)

            self.closed = window.events.closed
            self.closing = window.events.closing
            self.shown = window.events.shown
            self.loaded = window.events.loaded
            self.url = window.real_url
            self.TopMost = window.on_top

            self.is_fullscreen = False
            if window.fullscreen:
                self.toggle_fullscreen()

            hwnd = self.Handle.ToInt32()

            if window.shadow and not window.transparent:
                # Should do this before set frameless
                ExtendFrameIntoClientArea(hwnd)
                DwmSetWindowAttribute(hwnd, 2, 2, 4)

            if window.frameless:
                self.frameless = window.frameless
                self.FormBorderStyle = getattr(WinForms.FormBorderStyle, 'None')

            if window.menu or _state['menu']:
                self.set_window_menu(window.menu or _state['menu'])

            # Install frameless resize support *before* creating the browser,
            # because EdgeChrome reads self._frameless_resize_border to decide
            # whether to reserve a non-client border for system resize.
            if window.frameless and window.resizable:
                try:
                    self._install_frameless_resize()
                except Exception as e:
                    logger.warning('Failed to install frameless resize support: %s', e)

            if is_cef:
                self.browser = None
                CEF.create_browser(window, hwnd, BrowserView.alert, self)
            elif is_chromium:
                self.browser = Chromium.EdgeChrome(self, window, cache_dir)
                self.webview = self.browser.webview
            else:
                self.browser = IE.MSHTML(self, window, BrowserView.alert)
                self.webview = self.browser.webview

            if (
                window.transparent and self.browser
            ):  # window transparency is supported only with EdgeChromium
                self.SetStyle(WinForms.ControlStyles.SupportsTransparentBackColor, True)
                self.browser.DefaultBackgroundColor = Color.Transparent
            else:
                self.BackColor = ColorTranslator.FromHtml(window.background_color)

            if not window.focus:
                windll.user32.SetWindowLongW(
                    self.Handle.ToInt32(),
                    -20,
                    windll.user32.GetWindowLongW(self.Handle.ToInt32(), -20) | 0x8000000,
                )

            self.Activated += self.on_activated
            self.Shown += self.on_shown
            self.FormClosed += self.on_close
            self.FormClosing += self.on_closing
            self.Resize += self.on_resize
            self.Move += self.on_move

            self.localization = window.localization

            self.update_title_bar_theme()
            SystemEvents.UserPreferenceChanged += self.on_system_theme_changed

        def _install_frameless_resize(self):
            """Enable resizing for a frameless window.

            WinForms strips ``WS_THICKFRAME`` when ``FormBorderStyle = None``,
            so the system no longer offers resize handles at the edges. We add
            the style back and subclass the window procedure to make the window
            behave like a frameless window that is still resizable and keeps
            its native shadow.

            The implementation follows the approach used by Electron (and the
            reference ``borderless-window`` sample):

            * ``WM_NCACTIVATE`` — pass ``-1`` as the update region so
              DefWindowProc does not repaint the non-client border on
              activation changes.
            * ``WM_NCCALCSIZE`` — return 0 so the client area fills the whole
              window (no non-client area is visible).
            * ``WM_NCPAINT`` — forwarded to DefWindowProc so DWM still draws
              the window shadow (blocking it would remove the shadow too).
            * ``WM_NCUAHDRAWCAPTION`` / ``WM_NCUAHDRAWFRAME`` — these
              undocumented messages draw the themed window border. Block them
              to prevent the border from being drawn over the client area.
            * ``WM_NCHITTEST`` — answered with edge hit-test codes computed in
              client coordinates, so the system engages its resize modal loop
              when the cursor is near a window edge.
            * ``WM_SETCURSOR`` — shows the appropriate sizing cursor based on
              the hit-test result.

            ``DWMWA_NCRENDERING_POLICY`` is left at ``DWMNCRP_ENABLED`` (set
            earlier for the shadow) and ``WS_THICKFRAME`` is added back so the
            system resize modal loop works.
            """
            try:
                hwnd = self.Handle.ToInt32()

                sm_cxframe = windll.user32.GetSystemMetrics(32)  # SM_CXFRAME
                sm_cxpadborder = windll.user32.GetSystemMetrics(92)  # SM_CXPADDEDBORDER
                frame_size = sm_cxframe + sm_cxpadborder
                diagonal_width = frame_size * 2 + windll.user32.GetSystemMetrics(5)  # SM_CXBORDER

                def _hit_test_client(hwnd, lparam):
                    screen_x = ctypes.c_short(lparam & 0xFFFF).value
                    screen_y = ctypes.c_short((lparam >> 16) & 0xFFFF).value

                    pt = wintypes.POINT()
                    pt.x = screen_x
                    pt.y = screen_y
                    windll.user32.ScreenToClient(wintypes.HWND(hwnd), ctypes.byref(pt))

                    rect = wintypes.RECT()
                    windll.user32.GetClientRect(wintypes.HWND(hwnd), ctypes.byref(rect))
                    width = rect.right - rect.left
                    height = rect.bottom - rect.top

                    on_top = pt.y < frame_size
                    on_bottom = pt.y >= height - frame_size
                    on_left = pt.x < diagonal_width
                    on_right = pt.x >= width - diagonal_width

                    if on_top and on_left:
                        return _HTTOPLEFT
                    if on_top and on_right:
                        return _HTTOPRIGHT
                    if on_bottom and on_left:
                        return _HTBOTTOMLEFT
                    if on_bottom and on_right:
                        return _HTBOTTOMRIGHT
                    if on_top:
                        return _HTTOP
                    if on_bottom:
                        return _HTBOTTOM
                    if pt.x < frame_size:
                        return _HTLEFT
                    if pt.x >= width - frame_size:
                        return _HTRIGHT
                    return _HTCLIENT

                parent_original = _get_window_long_ptr(hwnd, _GWLP_WNDPROC)

                def parent_wnd_proc(hwnd, msg, wparam, lparam):
                    if msg == _WM_NCACTIVATE:
                        return _CallWindowProcW(
                            ctypes.c_void_p(parent_original),
                            wintypes.HWND(hwnd),
                            msg,
                            wparam,
                            -1,
                        )
                    elif msg == _WM_NCCALCSIZE and wparam:
                        return 0
                    elif msg in (_WM_NCUAHDRAWCAPTION, _WM_NCUAHDRAWFRAME):
                        return 0
                    elif msg == _WM_NCHITTEST:
                        if windll.user32.IsZoomed(wintypes.HWND(hwnd)):
                            return _HTCLIENT
                        hit = _hit_test_client(hwnd, lparam)
                        if hit != _HTCLIENT:
                            return hit
                    elif msg == _WM_SETCURSOR:
                        hit_test = (wparam >> 16) & 0xFFFF
                        cursor_id = _RESIZE_CURSORS.get(hit_test)
                        if cursor_id is not None:
                            cursor_handle = windll.user32.LoadCursorW(0, cursor_id)
                            windll.user32.SetCursor(cursor_handle)
                            return 1

                    return _CallWindowProcW(
                        ctypes.c_void_p(parent_original),
                        wintypes.HWND(hwnd),
                        msg,
                        wparam,
                        lparam,
                    )

                parent_callback = _WNDPROC(parent_wnd_proc)
                self._frameless_resize_parent_ref = parent_callback
                _set_window_long_ptr(
                    hwnd, _GWLP_WNDPROC, ctypes.cast(parent_callback, ctypes.c_void_p).value
                )

                style = _get_window_long_ptr(hwnd, _GWL_STYLE)
                _set_window_long_ptr(hwnd, _GWL_STYLE, style | _WS_THICKFRAME)

                self._frameless_resize_border = frame_size
            except Exception as e:
                logger.warning('Frameless resize setup failed: %s', e)

        def __str__(self):
            return f'<System.Windows.Forms object with {self.Handle} handle>'

        @property
        def _scale(self):
            """Logical-to-physical pixel scale for the monitor this window is on."""
            if is_chromium:
                try:
                    # Use per-window DPI for accurate multi-monitor support
                    return windll.user32.GetDpiForWindow(self.Handle.ToInt32()) / 96
                except Exception as e:
                    logger.warning(f'Failed to get DPI for window: {e}')
                    return 1.0
            else:
                # MSHTML doesn't need scaling
                return 1.0

        def on_system_theme_changed(self, sender, e):
            self.update_title_bar_theme()

        def update_title_bar_theme(self):
            if self.is_dark_theme():
                DwmSetWindowAttribute(self.Handle.ToInt32(), 20, 1)
                DwmSetWindowAttribute(self.Handle.ToInt32(), 38, 2)
            else:
                DwmSetWindowAttribute(self.Handle.ToInt32(), 20, 0)
                DwmSetWindowAttribute(self.Handle.ToInt32(), 38, 1)

        def is_dark_theme(self):
            try:
                personalize_key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize',
                    0,
                    winreg.KEY_READ,
                )
                system_theme, _ = winreg.QueryValueEx(personalize_key, 'AppsUseLightTheme')
                winreg.CloseKey(personalize_key)
                if system_theme == 0:
                    return True
                else:
                    return False
            except Exception as e:
                logger.debug(f'Error while getting system theme: {e}')
                return None

        def on_activated(self, *_):
            if not self.pywebview_window.focus:
                windll.user32.SetWindowLongW(
                    self.Handle.ToInt32(),
                    -20,
                    windll.user32.GetWindowLongW(self.Handle.ToInt32(), -20) | 0x8000000,
                )

        def on_shown(self, *_):
            if not is_cef:
                self.shown.set()
                self.browser.webview.Focus()

        def on_close(self, *_):
            def _shutdown():
                if is_cef:
                    CEF.shutdown()
                elif is_chromium:
                    self.hide()
                    self.browser.clear_user_data()

                WinForms.Application.Exit()

            if not is_cef:
                # stop waiting for JS result
                self.browser.js_result_semaphore.release()

            if is_cef:
                CEF.close_window(self.uid)

            del BrowserView.instances[self.uid]

            # during tests windows is empty for some reason. no idea why.
            if self.pywebview_window in windows:
                windows.remove(self.pywebview_window)

            self.closed.set()

            if len(BrowserView.instances) == 0:
                self.Invoke(Func[Type](_shutdown))

        def on_closing(self, sender, args):
            should_cancel = self.closing.set()
            if should_cancel:
                args.Cancel = True

            if not args.Cancel:
                if self.pywebview_window.confirm_close:
                    result = WinForms.MessageBox.Show(
                        self.localization['global.quitConfirmation'],
                        self.Text,
                        WinForms.MessageBoxButtons.OKCancel,
                        WinForms.MessageBoxIcon.Asterisk,
                    )

                    if result == WinForms.DialogResult.Cancel:
                        args.Cancel = True

        def on_resize(self, sender, args):
            if self.WindowState == WinForms.FormWindowState.Maximized:
                self.pywebview_window.events.maximized.set()

            if self.WindowState == WinForms.FormWindowState.Minimized:
                self.pywebview_window.events.minimized.set()

            if self.WindowState == WinForms.FormWindowState.Normal and self.old_state in (
                WinForms.FormWindowState.Minimized,
                WinForms.FormWindowState.Maximized,
            ):
                self.pywebview_window.events.restored.set()

            self.old_state = self.WindowState

            if is_cef:
                CEF.resize(self.Width, self.Height, self.uid)

            # Convert physical pixel dimensions to logical pixels for the API
            scale = self._scale
            self.pywebview_window.events.resized.set(
                int(self.Width / scale), int(self.Height / scale)
            )

        def on_move(self, sender, args):
            # Convert physical pixel location to logical pixels for the API
            scale = self._scale
            self.pywebview_window.events.moved.set(
                int(self.Location.X / scale),
                int(self.Location.Y / scale),
            )

        def evaluate_js(self, script, parse_json):
            result = self.browser.evaluate_js(script, parse_json)
            return result

        def clear_cookies(self):
            def _clear_cookies():
                self.browser.clear_cookies()

            if not is_chromium:
                logger.error('clear_cookies() is not implemented for this platform')
                return

            self.Invoke(Func[Type](_clear_cookies))

        def get_cookies(self):
            def _get_cookies():
                self.browser.get_cookies(cookies, semaphore)

            cookies = []
            if not is_chromium:
                logger.error('get_cookies() is not implemented for this platform')
                return cookies

            semaphore = Semaphore(0)

            self.Invoke(Func[Type](_get_cookies))
            semaphore.acquire()

            return cookies

        def load_html(self, content, base_uri):
            def _load_html():
                self.browser.load_html(content, base_uri)

            self.Invoke(Func[Type](_load_html))

        def load_url(self, url):
            def _load_url():
                self.browser.load_url(url)

            self.Invoke(Func[Type](_load_url))

        def hide(self):
            self.Invoke(Func[Type](self.Hide))

        def show(self):
            def _show():
                self.Show()
                self.Activate()

            if self.InvokeRequired:
                self.Invoke(Func[Type](_show))
            else:
                _show()

        def set_window_menu(self, menu_list):
            def _set_window_menu():
                def create_action_item(menu_line_item):
                    action_item = WinForms.ToolStripMenuItem(menu_line_item.title)
                    # Don't run action function on main thread
                    action_item.Click += (
                        lambda _, __, menu_line_item=menu_line_item: threading.Thread(
                            target=menu_line_item.function
                        ).start()
                    )
                    return action_item

                def create_submenu(title, line_items, supermenu=None):
                    m = WinForms.ToolStripMenuItem(title)
                    for menu_line_item in line_items:
                        if isinstance(menu_line_item, MenuSeparator):
                            m.DropDownItems.Add(WinForms.ToolStripSeparator())
                            continue
                        elif isinstance(menu_line_item, MenuAction):
                            m.DropDownItems.Add(create_action_item(menu_line_item))
                        elif isinstance(menu_line_item, Menu):
                            create_submenu(menu_line_item.title, menu_line_item.items, m)

                    if supermenu:
                        supermenu.DropDownItems.Add(m)

                    return m

                top_level_menu = WinForms.MenuStrip()

                for menu in menu_list:
                    # Ignore '__app__' menus (macOS-only feature)
                    if isinstance(menu, Menu) and menu.title == '__app__':
                        continue
                    if isinstance(menu, Menu):
                        top_level_menu.Items.Add(create_submenu(menu.title, menu.items))
                    elif isinstance(menu, MenuAction):
                        top_level_menu.Items.Add(create_action_item(menu))

                self.Controls.Add(top_level_menu)

            if self.InvokeRequired:
                self.Invoke(Func[Type](_set_window_menu))
            else:
                _set_window_menu()

        def toggle_fullscreen(self):
            def _toggle():
                if not self.is_fullscreen:
                    self.old_size = self.Size
                    self.old_state = self.WindowState
                    self.old_style = self.FormBorderStyle
                    self.old_location = self.Location
                    self.old_screen = WinForms.Screen.FromControl(self)
                    self.FormBorderStyle = getattr(WinForms.FormBorderStyle, 'None')
                    self.Bounds = WinForms.Screen.FromControl(self).Bounds
                    self.WindowState = WinForms.FormWindowState.Maximized
                    self.is_fullscreen = True
                    windll.user32.SetWindowPos(
                        self.Handle.ToInt32(),
                        None,
                        self.old_screen.Bounds.X,
                        self.old_screen.Bounds.Y,
                        self.old_screen.Bounds.Width,
                        self.old_screen.Bounds.Height,
                        64,
                    )
                    # disable window rounding
                    DwmSetWindowAttribute(self.Handle.ToInt32(), 33, 1)
                    # hide window border
                    DwmSetWindowAttribute(self.Handle.ToInt32(), 34, 0xFFFFFFFE)
                else:
                    self.WindowState = WinForms.FormWindowState.Normal
                    self.FormBorderStyle = self.old_style
                    self.is_fullscreen = False
                    valid_location = any(
                        screen == self.old_screen for screen in WinForms.Screen.AllScreens
                    )

                    if not valid_location:
                        self.Size = self.old_size
                        self.CenterToScreen()
                    else:
                        self.Location = self.old_location
                        self.Size = self.old_size

                    # enable window rounding
                    DwmSetWindowAttribute(self.Handle.ToInt32(), 33, 0)
                    # show window border
                    DwmSetWindowAttribute(self.Handle.ToInt32(), 34, 0xFFFFFFFF)

            if self.InvokeRequired:
                self.Invoke(Func[Type](_toggle))
            else:
                _toggle()

        def resize(self, width, height, fix_point):
            # Input width/height are in logical pixels, need to convert to physical
            scale = self._scale
            phys_width = int(width * scale)
            phys_height = int(height * scale)

            # Location is already in physical pixels
            x = self.Location.X
            y = self.Location.Y

            if fix_point & FixPoint.EAST:
                x = x + self.Width - phys_width

            if fix_point & FixPoint.SOUTH:
                y = y + self.Height - phys_height

            windll.user32.SetWindowPos(
                self.Handle.ToInt32(), None, x, y, phys_width, phys_height, 64
            )

        def move(self, x, y):
            # Input x/y are in logical pixels, need to convert to physical
            SWP_NOSIZE = 0x0001  # Retains the current size
            SWP_NOZORDER = 0x0004  # Retains the current Z order
            SWP_SHOWWINDOW = 0x0040  # Displays the window

            scale = self._scale
            if scale != 1:
                # Convert logical pixels to physical pixels
                x_phys = int(x * scale)
                y_phys = int(y * scale)
            else:
                x_phys = int(x)
                y_phys = int(y)

            windll.user32.SetWindowPos(
                self.Handle.ToInt32(),
                None,
                x_phys,
                y_phys,
                None,
                None,
                SWP_NOSIZE | SWP_NOZORDER | SWP_SHOWWINDOW,
            )

        def maximize(self):
            def _maximize():
                self.WindowState = WinForms.FormWindowState.Maximized

            self.Invoke(Func[Type](_maximize))

        def minimize(self):
            def _minimize():
                self.WindowState = WinForms.FormWindowState.Minimized

            self.Invoke(Func[Type](_minimize))

        def restore(self):
            def _restore():
                self.WindowState = WinForms.FormWindowState.Normal

            self.Invoke(Func[Type](_restore))

        def set_on_top(self, on_top):
            def _set_on_top():
                self.TopMost = on_top

            if self.InvokeRequired:
                self.Invoke(Func[Type](_set_on_top))
            else:
                _set_on_top()

    @staticmethod
    def alert(message):
        WinForms.MessageBox.Show(str(message))


class OpenFolderDialog:
    foldersFilter = 'Folders|\n'
    flags = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic
    windowsFormsAssembly = Assembly.LoadWithPartialName('System.Windows.Forms')
    iFileDialogType = windowsFormsAssembly.GetType(
        'System.Windows.Forms.FileDialogNative+IFileDialog'
    )
    OpenFileDialogType = windowsFormsAssembly.GetType('System.Windows.Forms.OpenFileDialog')
    FileDialogType = windowsFormsAssembly.GetType('System.Windows.Forms.FileDialog')
    createVistaDialogMethodInfo = OpenFileDialogType.GetMethod('CreateVistaDialog', flags)
    onBeforeVistaDialogMethodInfo = OpenFileDialogType.GetMethod('OnBeforeVistaDialog', flags)
    getOptionsMethodInfo = FileDialogType.GetMethod('GetOptions', flags)
    setOptionsMethodInfo = iFileDialogType.GetMethod('SetOptions', flags)
    fosPickFoldersBitFlag = (
        windowsFormsAssembly.GetType('System.Windows.Forms.FileDialogNative+FOS')
        .GetField('FOS_PICKFOLDERS')
        .GetValue(None)
    )

    vistaDialogEventsConstructorInfo = windowsFormsAssembly.GetType(
        'System.Windows.Forms.FileDialog+VistaDialogEvents'
    ).GetConstructor(flags, None, [FileDialogType], [])
    adviseMethodInfo = iFileDialogType.GetMethod('Advise')
    unadviseMethodInfo = iFileDialogType.GetMethod('Unadvise')
    showMethodInfo = iFileDialogType.GetMethod('Show')

    @classmethod
    def show(cls, parent=None, initialDirectory=None, allow_multiple=False, title=None):
        openFileDialog = WinForms.OpenFileDialog()
        openFileDialog.InitialDirectory = initialDirectory
        openFileDialog.Title = title
        openFileDialog.Filter = OpenFolderDialog.foldersFilter
        openFileDialog.AddExtension = False
        openFileDialog.CheckFileExists = False
        openFileDialog.DereferenceLinks = True
        openFileDialog.Multiselect = allow_multiple
        openFileDialog.RestoreDirectory = True

        iFileDialog = OpenFolderDialog.createVistaDialogMethodInfo.Invoke(openFileDialog, [])
        OpenFolderDialog.onBeforeVistaDialogMethodInfo.Invoke(openFileDialog, [iFileDialog])
        options = OpenFolderDialog.getOptionsMethodInfo.Invoke(openFileDialog, [])
        options = options.op_BitwiseOr(OpenFolderDialog.fosPickFoldersBitFlag)
        OpenFolderDialog.setOptionsMethodInfo.Invoke(iFileDialog, [options])
        adviseParametersWithOutputConnectionToken = Array[Object](
            [
                OpenFolderDialog.vistaDialogEventsConstructorInfo.Invoke([openFileDialog]),
                UInt32(0),
            ]
        )
        OpenFolderDialog.adviseMethodInfo.Invoke(
            iFileDialog, adviseParametersWithOutputConnectionToken
        )
        dwCookie = adviseParametersWithOutputConnectionToken.GetValue(1)
        try:
            result = OpenFolderDialog.showMethodInfo.Invoke(
                iFileDialog, [parent.Handle if parent else None]
            )
            if result == 0:
                return tuple(openFileDialog.FileNames)

            return None

        finally:
            OpenFolderDialog.unadviseMethodInfo.Invoke(iFileDialog, [UInt32(dwCookie)])


_main_window_created = Event()
_main_window_created.clear()

_already_set_up_app = False


def init_storage():
    global cache_dir

    if not _state['private_mode'] or _state['storage_path']:
        try:
            data_folder = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData)

            if not os.access(data_folder, os.W_OK):
                data_folder = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile)

            cache_dir = _state['storage_path'] or os.path.join(data_folder, 'pywebview')

            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir)
        except Exception:
            logger.exception(f'Cache directory {cache_dir} creation failed')
    else:
        cache_dir = tempfile.TemporaryDirectory().name


def setup_app():
    # MUST be called before create_window
    global _already_set_up_app
    if _already_set_up_app:
        return

    WinForms.Application.EnableVisualStyles()
    WinForms.Application.SetCompatibleTextRenderingDefault(False)
    _already_set_up_app = True


def create_window(window):
    def create():
        browser = BrowserView.BrowserForm(window, cache_dir)
        BrowserView.instances[window.uid] = browser
        window.events.before_show.set()

        if window.hidden:
            browser.Opacity = 0
            browser.Show()
            browser.Hide()
            browser.Opacity = 1
        elif window.transparent and is_chromium:
            # hack to make transparent window work
            # window is started hidden and shown on Navigating event.
            # no idea why this works
            browser.Show()
            browser.Hide()
        else:
            browser.Show()

        _main_window_created.set()

        if window.uid == 'master':

            def timer_tick(sender, e):
                # Check if SIGINT was received and exit from GUI thread
                global _sigint_received
                if _sigint_received:
                    app.Exit()

            # Create a timer to periodically allow the Python interpreter to run
            # This enables the signal handler to be called even when the WinForms event loop is running
            timer = WinForms.Timer()
            timer.Interval = 500  # 500ms
            timer.Tick += timer_tick
            timer.Start()

            app.Run()

    app = WinForms.Application

    if window.uid == 'master':
        # Set up Ctrl+C handler in main thread (before starting GUI thread)
        signal.signal(signal.SIGINT, _sigint_handler)

        if is_chromium:
            init_storage()

        if sys.getwindowsversion().major >= 6:
            windll.user32.SetProcessDPIAware()

        if is_cef:
            CEF.init(window, cache_dir)

        thread = Thread(ThreadStart(create))
        thread.SetApartmentState(ApartmentState.STA)
        thread.Start()

        # Don't use thread.Join() as it blocks the main thread indefinitely,
        # preventing signal handlers from being processed. Instead, periodically
        # check if the thread is still alive, which allows the Python interpreter
        # to process pending signals (like SIGINT from Ctrl+C)
        while thread.IsAlive:
            thread.Join(500)

    else:
        _main_window_created.wait()
        i = list(BrowserView.instances.values())[0]  # arbitrary instance
        i.Invoke(Func[Type](create))


def set_title(title, uid):
    def _set_title():
        i.Text = title

    i = BrowserView.instances.get(uid)

    if not i:
        return
    elif i.InvokeRequired:
        i.Invoke(Func[Type](_set_title))
    else:
        _set_title()


def create_confirmation_dialog(title, message, uid):
    i = BrowserView.instances.get(uid)

    if not i:
        return

    result = WinForms.MessageBox.Show(message, title, WinForms.MessageBoxButtons.OKCancel)
    return result == WinForms.DialogResult.OK


def create_file_dialog(dialog_type, directory, allow_multiple, save_filename, file_types, uid):
    i = BrowserView.instances.get(uid)

    if not i:
        return

    if not directory:
        directory = os.environ['HOMEPATH']

    try:
        if dialog_type == FileDialog.FOLDER:
            file_path = OpenFolderDialog.show(i, directory, allow_multiple)

        elif dialog_type == FileDialog.OPEN:
            dialog = WinForms.OpenFileDialog()

            dialog.Multiselect = allow_multiple
            dialog.InitialDirectory = directory

            if len(file_types) > 0:
                dialog.Filter = '|'.join(
                    ['{0} ({1})|{1}'.format(*parse_file_type(f)) for f in file_types]
                )
            else:
                dialog.Filter = i.localization['windows.fileFilter.allFiles'] + ' (*.*)|*.*'
            dialog.RestoreDirectory = True

            result = dialog.ShowDialog(i)
            if result == WinForms.DialogResult.OK:
                file_path = tuple(dialog.FileNames)
            else:
                file_path = None

        elif dialog_type == FileDialog.SAVE:
            dialog = WinForms.SaveFileDialog()
            if len(file_types) > 0:
                dialog.Filter = '|'.join(
                    ['{0} ({1})|{1}'.format(*parse_file_type(f)) for f in file_types]
                )
            else:
                dialog.Filter = i.localization['windows.fileFilter.allFiles'] + ' (*.*)|*.*'
            dialog.InitialDirectory = directory
            dialog.RestoreDirectory = True
            dialog.FileName = save_filename

            result = dialog.ShowDialog(i)
            if result == WinForms.DialogResult.OK:
                file_path = (dialog.FileName,)
            else:
                file_path = None

        return file_path
    except Exception as e:
        logger.exception(f'Error invoking {dialog_type} dialog: {e}')
        return None


def clear_cookies(uid):
    if is_cef:
        CEF.clear_cookies(uid)
    i = BrowserView.instances.get(uid)

    if i:
        i.clear_cookies()


def get_cookies(uid):
    if is_cef:
        return CEF.get_cookies(uid)
    i = BrowserView.instances.get(uid)

    if i:
        return i.get_cookies()


def get_current_url(uid):
    if is_cef:
        return CEF.get_current_url(uid)

    i = BrowserView.instances.get(uid)
    if i:
        return i.browser.url


def load_url(url, uid):
    i = BrowserView.instances.get(uid)
    if not i:
        return

    if is_cef:
        CEF.load_url(url, uid)
    else:
        i.load_url(url)


def load_html(content, base_uri, uid):
    i = BrowserView.instances.get(uid)

    if is_cef:
        CEF.load_html(inject_base_uri(content, base_uri), uid)
    elif i:
        i.load_html(content, base_uri)


def get_active_window():
    active_window = None
    try:
        active_window = WinForms.Form.ActiveForm
    except Exception:
        return None

    if active_window:
        for uid, browser_view_instance in BrowserView.instances.items():
            if browser_view_instance.Handle == active_window.Handle:
                return browser_view_instance.pywebview_window

    return None


def show(uid):
    i = BrowserView.instances.get(uid)
    if i:
        i.show()


def hide(uid):
    i = BrowserView.instances.get(uid)
    if i:
        i.hide()


def toggle_fullscreen(uid):
    i = BrowserView.instances.get(uid)
    if i:
        i.toggle_fullscreen()


def set_on_top(uid, on_top):
    i = BrowserView.instances.get(uid)
    if i:
        i.set_on_top(on_top)


def resize(width, height, uid, fix_point):
    i = BrowserView.instances.get(uid)
    if i:
        i.resize(width, height, fix_point)


def move(x, y, uid):
    i = BrowserView.instances.get(uid)
    if i:
        i.move(x, y)


def maximize(uid):
    i = BrowserView.instances.get(uid)
    if i:
        i.maximize()


def minimize(uid):
    i = BrowserView.instances.get(uid)
    if i:
        i.minimize()


def restore(uid):
    i = BrowserView.instances.get(uid)
    if i:
        i.restore()


def destroy_window(uid):
    def _close():
        i.Close()

    i = BrowserView.instances.get(uid)
    if not i:
        return

    i.Invoke(Func[Type](_close))
    if not is_cef:
        i.browser.js_result_semaphore.release()


def evaluate_js(script, uid, parse_json, result_id=None):
    if is_cef:
        return CEF.evaluate_js(script, result_id, parse_json, uid)

    i = BrowserView.instances.get(uid)
    if i:
        return i.evaluate_js(script, parse_json)


def get_position(uid):
    i = BrowserView.instances.get(uid)
    if i:
        # Convert physical pixel position to logical pixels
        scale = i._scale
        return int(i.Left / scale), int(i.Top / scale)


def get_size(uid):
    i = BrowserView.instances.get(uid)
    if i:
        # Size is in physical pixels, convert to logical pixels
        size = i.Size
        scale = i._scale
        return int(size.Width / scale), int(size.Height / scale)


def get_screens():
    """Get all screens with coordinates in logical pixels."""
    screens = []

    for s in WinForms.Screen.AllScreens:
        # Get logical size from Bounds (already DPI-aware scaled due to SetProcessDPIAware)
        logical_width = s.Bounds.Width
        logical_height = s.Bounds.Height

        # Get scale factor by comparing physical vs logical resolution
        scale = win32.get_screen_scale(s.DeviceName, logical_width, logical_height)

        # Bounds are already in logical pixels due to SetProcessDPIAware
        screens.append(
            Screen(
                s.Bounds.X,
                s.Bounds.Y,
                logical_width,
                logical_height,
                s.WorkingArea,
                scale,
            )
        )

    return screens


def add_tls_cert(_):
    return
