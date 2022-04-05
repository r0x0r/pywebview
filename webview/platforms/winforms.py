# -*- coding: utf-8 -*-

"""
(C) 2014-2019 Roman Sirokov and contributors
Licensed under BSD license
http://github.com/r0x0r/pywebview/
"""

import os
import sys
import logging
from threading import Event
import ctypes
from ctypes import windll
from uuid import uuid4
from platform import machine
import time

from webview import windows, OPEN_DIALOG, FOLDER_DIALOG, SAVE_DIALOG
from webview.guilib import forced_gui_
from webview.util import parse_file_type, inject_base_uri
from webview.js import alert
from webview.screen import Screen
from webview.window import FixPoint

try:
    import _winreg as winreg  # Python 2
except ImportError:
    import winreg  # Python 3

import clr

clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Collections')
clr.AddReference('System.Threading')

import System.Windows.Forms as WinForms
from System import IntPtr, Int32, Func, Type, Environment, Uri
from System.Threading import Thread, ThreadStart, ApartmentState
from System.Drawing import Size, Point, Icon, Color, ColorTranslator, SizeF

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

logger = logging.getLogger('pywebview')

settings = {}

def _is_edge():
    try:
        net_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full')
        version, _ = winreg.QueryValueEx(net_key, 'Release')

        windows_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows NT\CurrentVersion')
        build, _ = winreg.QueryValueEx(windows_key, 'CurrentBuild')
        build = int(build)

        return version >= 394802 and build >= 17134 # .NET 4.6.2 + Windows 10 1803
    except Exception as e:
        logger.exception(e)
        return False
    finally:
        winreg.CloseKey(net_key)

def _is_new_version(current_version, new_version):
    new_range = new_version.split(".")
    cur_range = current_version.split(".")
    for index in range(len(new_range)):
        if len(cur_range) > index:
            return int(new_range[index]) >= int(cur_range[index])

    return False

def _is_chromium():
    def edge_build(key_type, key, description=''):
        try:
            windows_key = None
            if machine() == 'x86' or key_type == 'HKEY_CURRENT_USER':
                path = rf'Microsoft\EdgeUpdate\Clients\{key}'
            else:
                path = rf'WOW6432Node\Microsoft\EdgeUpdate\Clients\{key}'

            register_key = rf'Computer\{key_type}\{path}'
            windows_key = winreg.OpenKey(getattr(winreg, key_type), rf'SOFTWARE\{path}')
            build, _ = winreg.QueryValueEx(windows_key, 'pv')

            return str(build)
        except Exception as e:
            # Forming extra information
            extra_info = ''
            if description != '':
                extra_info = f'{description} Registry path: {register_key}'
            else:
                extra_info = f'Registry path: {register_key}'

            # Adding extra info to error
            e.strerror += ' - ' + extra_info
            logger.debug(e)

        try:
            winreg.CloseKey(windows_key)
        except:
            pass

        return '0'

    try:
        net_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full')
        version, _ = winreg.QueryValueEx(net_key, 'Release')

        if version < 394802: # .NET 4.6.2
            return False

        build_versions = [
            {'key':'{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'description':'Microsoft Edge WebView2 Runtime'},  # runtime
            {'key':'{2CD8A007-E189-409D-A2C8-9AF4EF3C72AA}', 'description':'Microsoft Edge WebView2 Beta'}, # beta
            {'key':'{0D50BFEC-CD6A-4F9A-964C-C7416E3ACB10}', 'description':'Microsoft Edge WebView2 Developer'}, # dev
            {'key':'{65C35B14-6C1D-4122-AC46-7148CC9D6497}', 'description':'Microsoft Edge WebView2 Canary'}, # canary
        ]

        for item in build_versions:
            for key_type in ('HKEY_CURRENT_USER', 'HKEY_LOCAL_MACHINE'):
                build = edge_build(key_type, item['key'], item['description'])

                if _is_new_version('86.0.622.0', build): # Webview2 86.0.622.0
                    return True

    except Exception as e:
        logger.exception(e)
    finally:
        winreg.CloseKey(net_key)

    return False


is_cef = forced_gui_ == 'cef'
is_chromium = not is_cef and _is_chromium() and forced_gui_ not in ['mshtml', 'edgehtml']
is_edge = not is_chromium and _is_edge() and forced_gui_ != 'mshtml'


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
elif is_edge:
    from . import edgehtml as Edge
    IWebBrowserInterop = object

    logger.warning('EdgeHTML is deprecated. See https://pywebview.flowrl.com/guide/renderer.html#web-engine on details how to use Edge Chromium')
    renderer = 'edgehtml'
else:
    from . import mshtml as IE
    logger.warning('MSHTML is deprecated. See https://pywebview.flowrl.com/guide/renderer.html#web-engine on details how to use Edge Chromium')
    logger.debug('Using WinForms / MSHTML')
    renderer = 'mshtml'


class BrowserView:
    instances = {}

    class BrowserForm(WinForms.Form):
        def __init__(self, window):
            self.uid = window.uid
            self.pywebview_window = window
            self.real_url = None
            self.Text = window.title
            self.Size = Size(window.initial_width, window.initial_height)
            self.MinimumSize = Size(window.min_size[0], window.min_size[1])

            if window.initial_x is not None and window.initial_y is not None:
                self.StartPosition = WinForms.FormStartPosition.Manual
                self.Location = Point(window.initial_x, window.initial_y)
            else:
                self.StartPosition = WinForms.FormStartPosition.CenterScreen

            self.AutoScaleDimensions = SizeF(96.0, 96.0)
            self.AutoScaleMode = WinForms.AutoScaleMode.Dpi

            if not window.resizable:
                self.FormBorderStyle = WinForms.FormBorderStyle.FixedSingle
                self.MaximizeBox = False

            if window.minimized:
                self.WindowState = WinForms.FormWindowState.Minimized

            self.old_state =  self.WindowState

            # Application icon
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
            self.text_select = window.text_select
            self.on_top = window.on_top

            self.is_fullscreen = False
            if window.fullscreen:
                self.toggle_fullscreen()

            if window.frameless:
                self.frameless = window.frameless
                self.FormBorderStyle = getattr(WinForms.FormBorderStyle, 'None')
            if is_cef:
                self.browser = None
                CEF.create_browser(window, self.Handle.ToInt32(), BrowserView.alert)
            elif is_chromium:
                self.browser = Chromium.EdgeChrome(self, window)
            elif is_edge:
                self.browser = Edge.EdgeHTML(self, window)
            else:
                self.browser = IE.MSHTML(self, window, BrowserView.alert)

            if window.transparent and self.browser: # window transparency is supported only with EdgeChromium
                self.BackColor = Color.LimeGreen
                self.TransparencyKey = Color.LimeGreen
                self.SetStyle(WinForms.ControlStyles.SupportsTransparentBackColor, True)
                self.browser.DefaultBackgroundColor = Color.Transparent
            else:
                self.BackColor = ColorTranslator.FromHtml(window.background_color)

            self.Activated += self.on_activated
            self.Shown += self.on_shown
            self.FormClosed += self.on_close
            self.FormClosing += self.on_closing
            self.Resize += self.on_resize

            self.localization = window.localization

        def on_activated(self, sender, args):
            if self.browser:
                self.browser.web_view.Focus()

            if is_cef:
                CEF.focus(self.uid)

        def on_shown(self, sender, args):
            if is_cef:
                CEF.focus(self.uid)
            else:
                self.shown.set()
                self.browser.web_view.Focus()

        def on_close(self, sender, args):
            def _shutdown():
                if is_cef:
                    CEF.shutdown()
                WinForms.Application.Exit()

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
            if self.pywebview_window.confirm_close:
                result = WinForms.MessageBox.Show(self.localization['global.quitConfirmation'], self.Text,
                                                WinForms.MessageBoxButtons.OKCancel, WinForms.MessageBoxIcon.Asterisk)

                if result == WinForms.DialogResult.Cancel:
                    args.Cancel = True

            if not args.Cancel:
                should_cancel = self.closing.set()

                if should_cancel:
                    args.Cancel = True

        def on_resize(self, sender, args):
            if self.WindowState == WinForms.FormWindowState.Maximized:
                self.pywebview_window.events.maximized.set()

            if self.WindowState == WinForms.FormWindowState.Minimized:
                self.pywebview_window.events.minimized.set()

            if self.WindowState == WinForms.FormWindowState.Normal and self.old_state in (WinForms.FormWindowState.Minimized, WinForms.FormWindowState.Maximized):
                self.pywebview_window.events.restored.set()

            self.old_state = self.WindowState

            if is_cef:
                CEF.resize(self.Width, self.Height, self.uid)

            self.pywebview_window.events.resized.set(self.Width, self.Height)

        def evaluate_js(self, script):
            id = uuid4().hex[:8]
            def _evaluate_js():
                self.browser.evaluate_js(script, id) if is_chromium or is_edge else self.browser.evaluate_js(script)

            self.loaded.wait()
            self.Invoke(Func[Type](_evaluate_js))
            self.browser.js_result_semaphore.acquire()

            if is_chromium or is_edge:
                if self.browser.js_results.get(id, None) is None:
                    time.sleep(.1)
                result = self.browser.js_results[id]
                self.browser.js_results.pop(id)
                return result

            return self.browser.js_result

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
            self.Invoke(Func[Type](self.Show))

        def toggle_fullscreen(self):
            def _toggle():
                screen = WinForms.Screen.FromControl(self)

                if not self.is_fullscreen:
                    self.old_size = self.Size
                    self.old_state = self.WindowState
                    self.old_style = self.FormBorderStyle
                    self.old_location = self.Location
                    self.FormBorderStyle = getattr(WinForms.FormBorderStyle, 'None')
                    self.Bounds = WinForms.Screen.PrimaryScreen.Bounds
                    self.WindowState = WinForms.FormWindowState.Maximized
                    self.is_fullscreen = True
                    windll.user32.SetWindowPos(self.Handle.ToInt32(), None, screen.Bounds.X, screen.Bounds.Y,
                                            screen.Bounds.Width, screen.Bounds.Height, 64)
                else:
                    self.Size = self.old_size
                    self.WindowState = self.old_state
                    self.FormBorderStyle = self.old_style
                    self.Location = self.old_location
                    self.is_fullscreen = False

            if self.InvokeRequired:
                self.Invoke(Func[Type](_toggle))
            else:
                _toggle()

        @property
        def on_top(self):
            return self.on_top

        @on_top.setter
        def on_top(self, on_top):
            def _set():
                z_order = -1 if on_top is True else -2
                SWP_NOSIZE = 0x0001  # Retains the current size
                windll.user32.SetWindowPos(self.Handle.ToInt32(), z_order, self.Location.X, self.Location.Y, None, None, SWP_NOSIZE)
            if self.InvokeRequired:
                self.Invoke(Func[Type](_set))
            else:
                _set()

        def resize(self, width, height, fix_point):

            x = self.Location.X
            y = self.Location.Y

            if fix_point & FixPoint.EAST:
                x = x + self.Width - width

            if fix_point & FixPoint.SOUTH:
                y = y + self.Height - height

            windll.user32.SetWindowPos(self.Handle.ToInt32(), None, x, y, width, height, 64)

        def move(self, x, y):
            SWP_NOSIZE = 0x0001  # Retains the current size
            SWP_NOZORDER = 0x0004  # Retains the current Z order
            SWP_SHOWWINDOW = 0x0040  # Displays the window
            windll.user32.SetWindowPos(self.Handle.ToInt32(), None, int(x), int(y), None, None,
                                    SWP_NOSIZE|SWP_NOZORDER|SWP_SHOWWINDOW)

        def minimize(self):
            def _minimize():
                self.WindowState = WinForms.FormWindowState.Minimized

            self.Invoke(Func[Type](_minimize))

        def restore(self):
            def _restore():
                self.WindowState = WinForms.FormWindowState.Normal

            self.Invoke(Func[Type](_restore))

    @staticmethod
    def alert(message):
        WinForms.MessageBox.Show(str(message))


def _set_ie_mode():
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
        ie_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Internet Explorer")
        try:
            version, type = winreg.QueryValueEx(ie_key, "svcVersion")
        except:
            version, type = winreg.QueryValueEx(ie_key, "Version")

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

    try:
        browser_emulation = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                           r"Software\Microsoft\Internet Explorer\Main\FeatureControl\FEATURE_BROWSER_EMULATION",
                                           0, winreg.KEY_ALL_ACCESS)
    except WindowsError:
        browser_emulation = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER,
                                               r"Software\Microsoft\Internet Explorer\Main\FeatureControl\FEATURE_BROWSER_EMULATION",
                                               0, winreg.KEY_ALL_ACCESS)

    try:
        dpi_support = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                     r"Software\Microsoft\Internet Explorer\Main\FeatureControl\FEATURE_96DPI_PIXEL",
                                     0, winreg.KEY_ALL_ACCESS)
    except WindowsError:
        dpi_support = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER,
                                               r"Software\Microsoft\Internet Explorer\Main\FeatureControl\FEATURE_96DPI_PIXEL",
                                               0, winreg.KEY_ALL_ACCESS)

    mode = get_ie_mode()
    executable_name = sys.executable.split("\\")[-1]
    winreg.SetValueEx(browser_emulation, executable_name, 0, winreg.REG_DWORD, mode)
    winreg.CloseKey(browser_emulation)

    winreg.SetValueEx(dpi_support, executable_name, 0, winreg.REG_DWORD, 1)
    winreg.CloseKey(dpi_support)


_main_window_created = Event()
_main_window_created.clear()

def create_window(window):
    def create():
        browser = BrowserView.BrowserForm(window)
        BrowserView.instances[window.uid] = browser

        if not window.hidden:
            browser.Show()

        _main_window_created.set()

        if window.uid == 'master':
            app.Run()

    app = WinForms.Application

    if window.uid == 'master':
        if not is_edge and not is_cef and not is_chromium:
            _set_ie_mode()

        if sys.getwindowsversion().major >= 6:
            windll.user32.SetProcessDPIAware()

        if is_cef:
            CEF.init(window)

        app.EnableVisualStyles()
        app.SetCompatibleTextRenderingDefault(False)
        thread = Thread(ThreadStart(create))
        thread.SetApartmentState(ApartmentState.STA)
        thread.Start()
        thread.Join()

    else:
        _main_window_created.wait()
        i = list(BrowserView.instances.values())[0]     # arbitrary instance
        i.Invoke(Func[Type](create))


def set_title(title, uid):
    def _set_title():
        window.Text = title

    window = BrowserView.instances[uid]
    if window.InvokeRequired:
        window.Invoke(Func[Type](_set_title))
    else:
        _set_title()


def create_file_dialog(dialog_type, directory, allow_multiple, save_filename, file_types, uid):
    window = BrowserView.instances[uid]

    if not directory:
        directory = os.environ['HOMEPATH']

    try:
        if dialog_type == FOLDER_DIALOG:
            dialog = WinForms.FolderBrowserDialog()
            dialog.RestoreDirectory = True

            if directory:
                dialog.SelectedPath = directory

            result = dialog.ShowDialog(window)
            if result == WinForms.DialogResult.OK:
                file_path = (dialog.SelectedPath,)
            else:
                file_path = None
        elif dialog_type == OPEN_DIALOG:
            dialog = WinForms.OpenFileDialog()

            dialog.Multiselect = allow_multiple
            dialog.InitialDirectory = directory

            if len(file_types) > 0:
                dialog.Filter = '|'.join(['{0} ({1})|{1}'.format(*parse_file_type(f)) for f in file_types])
            else:
                dialog.Filter = window.localization['windows.fileFilter.allFiles'] + ' (*.*)|*.*'
            dialog.RestoreDirectory = True

            result = dialog.ShowDialog(window)
            if result == WinForms.DialogResult.OK:
                file_path = tuple(dialog.FileNames)
            else:
                file_path = None

        elif dialog_type == SAVE_DIALOG:
            dialog = WinForms.SaveFileDialog()
            if len(file_types) > 0:
                dialog.Filter = '|'.join(['{0} ({1})|{1}'.format(*parse_file_type(f)) for f in file_types])
            else:
                dialog.Filter = window.localization['windows.fileFilter.allFiles'] + ' (*.*)|*.*'
            dialog.InitialDirectory = directory
            dialog.RestoreDirectory = True
            dialog.FileName = save_filename

            result = dialog.ShowDialog(window)
            if result == WinForms.DialogResult.OK:
                file_path = dialog.FileName
            else:
                file_path = None

        return file_path
    except:
        logger.exception('Error invoking {0} dialog'.format(dialog_type))
        return None


def get_current_url(uid):
    if is_cef:
        return CEF.get_current_url(uid)
    else:
        window = BrowserView.instances[uid]
        window.loaded.wait()
        return window.browser.url


def load_url(url, uid):
    window = BrowserView.instances[uid]
    window.loaded.clear()

    if is_cef:
        CEF.load_url(url, uid)
    else:
        window.load_url(url)


def load_html(content, base_uri, uid):
    if is_cef:
        CEF.load_html(inject_base_uri(content, base_uri), uid)
        return
    else:
        BrowserView.instances[uid].load_html(content, base_uri)


def show(uid):
    window = BrowserView.instances[uid]
    window.show()


def hide(uid):
    window = BrowserView.instances[uid]
    window.hide()


def toggle_fullscreen(uid):
    window = BrowserView.instances[uid]
    window.toggle_fullscreen()


def set_on_top(uid, on_top):
    window = BrowserView.instances[uid]
    window.on_top = on_top


def resize(width, height, uid, fix_point):
    window = BrowserView.instances[uid]
    window.resize(width, height, fix_point)


def move(x, y, uid):
    window = BrowserView.instances[uid]
    window.move(x, y)


def minimize(uid):
    window = BrowserView.instances[uid]
    window.minimize()


def restore(uid):
    window = BrowserView.instances[uid]
    window.restore()


def destroy_window(uid):
    def _close():
        window.Close()

    window = BrowserView.instances[uid]
    window.Invoke(Func[Type](_close))

    if not is_cef:
        window.browser.js_result_semaphore.release()


def evaluate_js(script, uid, result_id=None):
    if is_cef:
        return CEF.evaluate_js(script, result_id, uid)
    else:
        return BrowserView.instances[uid].evaluate_js(script)


def get_position(uid):
    return BrowserView.instances[uid].Left, BrowserView.instances[uid].Top


def get_size(uid):
    size = BrowserView.instances[uid].Size
    return size.Width, size.Height


def get_screens():
    screens = [Screen(s.Bounds.Width, s.Bounds.Height) for s in WinForms.Screen.AllScreens]
    return screens
