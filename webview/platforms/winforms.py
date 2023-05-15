# -*- coding: utf-8 -*-

"""
(C) 2014-2019 Roman Sirokov and contributors
Licensed under BSD license
http://github.com/r0x0r/pywebview/
"""

import os
import sys
import logging
import threading
from threading import Event, Semaphore
import ctypes
from ctypes import windll
from platform import machine
import tempfile

from webview import windows, _private_mode, _storage_path, OPEN_DIALOG, FOLDER_DIALOG, SAVE_DIALOG
from webview.guilib import forced_gui_
from webview.util import parse_file_type, inject_base_uri
from webview.screen import Screen
from webview.window import FixPoint
from webview.menu import Menu, MenuAction, MenuSeparator

import winreg
import clr

clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Collections')
clr.AddReference('System.Threading')

import System.Windows.Forms as WinForms
from System import IntPtr, Int32, Func, Type, Environment
from System.Threading import Thread, ThreadStart, ApartmentState
from System.Drawing import Size, Point, Icon, Color, ColorTranslator

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

logger = logging.getLogger('pywebview')

settings = {}


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

            with winreg.OpenKey(getattr(winreg, key_type), rf'SOFTWARE\{path}') as windows_key:
                build, _ = winreg.QueryValueEx(windows_key, 'pv')
                return str(build)

        except Exception as e:
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
    logger.warning('MSHTML is deprecated. See https://pywebview.flowrl.com/guide/renderer.html#web-engine on details how to use Edge Chromium')
    logger.debug('Using WinForms / MSHTML')
    renderer = 'mshtml'

if not _private_mode or _storage_path:
    try:
        data_folder = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData)
        
        if not os.access(data_folder, os.W_OK):
            data_folder = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile)
            
        cache_dir = _storage_path or os.path.join(data_folder, 'pywebview')

        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
    except Exception as e:
        logger.exception(f'Cache directory {cache_dir} creation failed')
else:
    cache_dir = tempfile.TemporaryDirectory().name

class BrowserView:
    instances = {}

    app_menu_list = None

    class BrowserForm(WinForms.Form):
        def __init__(self, window, cache_dir):
            super().__init__()
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
            self.TopMost = window.on_top
            self.scale_factor = 1

            self.is_fullscreen = False
            if window.fullscreen:
                self.toggle_fullscreen()

            if window.frameless:
                self.frameless = window.frameless
                self.FormBorderStyle = getattr(WinForms.FormBorderStyle, 'None')

            if BrowserView.app_menu_list:
                self.set_window_menu(BrowserView.app_menu_list)

            if is_cef:
                self.browser = None
                CEF.create_browser(window, self.Handle.ToInt32(), BrowserView.alert, self)
            elif is_chromium:
                self.browser = Chromium.EdgeChrome(self, window, cache_dir)
                # for chromium edge, need this factor to modify the coordinates
                self.scale_factor = windll.shcore.GetScaleFactorForDevice(0)/100
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
            self.Move += self.on_move

            self.localization = window.localization

        def on_activated(self, sender, args):
            if self.browser:
                self.browser.web_view.Focus()

            if is_cef:
                CEF.focus(self.uid)

        def on_shown(self, sender, args):
            if not is_cef:
                self.shown.set()
                self.browser.web_view.Focus()

        def on_close(self, sender, args):
            def _shutdown():
                if is_cef:
                    CEF.shutdown()
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

        def on_move(self, sender, args):
            self.pywebview_window.events.moved.set(self.Location.X, self.Location.Y)

        def evaluate_js(self, script):
            def _evaluate_js():
                self.browser.evaluate_js(script, semaphore, js_result) if is_chromium else self.browser.evaluate_js(script)

            semaphore = Semaphore(0)
            js_result = []

            self.loaded.wait()
            self.Invoke(Func[Type](_evaluate_js))
            semaphore.acquire()

            if is_chromium:
                result = js_result.pop()
                return result

            return self.browser.js_result

        def get_cookies(self):
            def _get_cookies():
                self.browser.get_cookies(cookies, semaphore)

            cookies = []
            if not is_chromium:
                logger.error('get_cookies() is not implemented for this platform')
                return cookies

            self.loaded.wait()

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
            if self.InvokeRequired:
                self.Invoke(Func[Type](self.Show))
            else:
                self.Show()

        def set_window_menu(self, menu_list):
            def _set_window_menu():
                def create_action_item(menu_line_item):
                    action_item = WinForms.ToolStripMenuItem(menu_line_item.title)
                    def on_click(_sender, _args, menu_line_item=menu_line_item):
                        # Don't run action function on main thread
                        from threading import Thread
                        Thread(target=menu_line_item.function).start()
                    action_item.Click += on_click
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
            if(self.scale_factor != 1):
                # The coordinates needed to be scaled
                x_modified = x * self.scale_factor
                y_modified = y * self.scale_factor
                windll.user32.SetWindowPos(self.Handle.ToInt32(), None, int(x_modified), int(y_modified), None, None, SWP_NOSIZE|SWP_NOZORDER|SWP_SHOWWINDOW)
            else:
                windll.user32.SetWindowPos(self.Handle.ToInt32(), None, int(x), int(y), None, None, SWP_NOSIZE|SWP_NOZORDER|SWP_SHOWWINDOW)

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

    import winreg

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

_already_set_up_app = False
def setup_app():
    # MUST be called before create_window and set_app_menu
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

        if window.hidden:
            browser.Opacity = 0
            browser.Show()
            browser.Hide()
            browser.Opacity = 1
        else:
            browser.Show()

        _main_window_created.set()

        if window.uid == 'master':
            app.Run()

    app = WinForms.Application

    if window.uid == 'master':
        if not is_cef and not is_chromium:
            _set_ie_mode()

        if sys.getwindowsversion().major >= 6:
            windll.user32.SetProcessDPIAware()

        if is_cef:
            CEF.init(window, cache_dir)

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


def create_confirmation_dialog(title, message, uid):
    result = WinForms.MessageBox.Show(message, title, WinForms.MessageBoxButtons.OKCancel)
    return result == WinForms.DialogResult.OK


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


def get_cookies(uid):
    if is_cef:
        return CEF.get_cookies(uid)
    else:
        window = BrowserView.instances[uid]
        return window.get_cookies()


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

def set_app_menu(app_menu_list):
    """
    Create a custom menu for the app bar menu (on supported platforms).
    Otherwise, this menu is used across individual windows.

    Args:
        app_menu_list ([webview.menu.Menu])
    """
    # WindowsForms doesn't allow controls to have more than one parent, so we
    #     save the app_menu_list and recreate the menu for each window as they
    #     are created.
    BrowserView.app_menu_list = app_menu_list

def get_active_window():
    active_window = None
    try:
        active_window = WinForms.Form.ActiveForm
    except:
        return None

    if active_window:
        for uid, browser_view_instance in BrowserView.instances.items():
            if browser_view_instance.Handle == active_window.Handle:
                return browser_view_instance.pywebview_window

    return None


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
    window.TopMost = on_top


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

def add_tls_cert(certfile):
    raise NotImplementedError

