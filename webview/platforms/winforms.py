import ctypes
import logging
import os
import sys
import tempfile
import threading
import winreg
from ctypes import windll
from ctypes import wintypes
from platform import machine
from threading import Event, Semaphore

import clr

from webview import FOLDER_DIALOG, OPEN_DIALOG, SAVE_DIALOG, _state, windows
from webview.guilib import forced_gui_
from webview.menu import Menu, MenuAction, MenuSeparator
from webview.screen import Screen
from webview.util import inject_base_uri, parse_file_type
from webview.window import FixPoint

clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Collections')
clr.AddReference('System.Threading')
clr.AddReference('System.Reflection')

import System.Windows.Forms as WinForms
from System import Environment, Func, Int32, IntPtr, Type, UInt32, Array, Object
from System.Drawing import Color, ColorTranslator, Icon, Point, Size, SizeF
from System.Threading import ApartmentState, Thread, ThreadStart
from System.Reflection import Assembly, BindingFlags

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
logger = logging.getLogger('pywebview')
cache_dir = None

def _is_new_version(current_version: str, new_version: str) -> bool:
    new_range = new_version.split('.')
    cur_range = current_version.split('.')
    for index, _ in enumerate(new_range):
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
    DwmSetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
    return DwmSetWindowAttribute(hwnd, attr, ctypes.byref(ctypes.c_int(value)), size)


def ExtendFrameIntoClientArea(hwnd):
    class _MARGINS(ctypes.Structure):
        _fields_ = [("cxLeftWidth", ctypes.c_int),
                    ("cxRightWidth", ctypes.c_int),
                    ("cyTopHeight", ctypes.c_int),
                    ("cyBottomHeight", ctypes.c_int)
                    ]

    DwmExtendFrameIntoClientArea = ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea
    m = _MARGINS()
    m.cxLeftWidth = 1
    m.cxRightWidth = 1
    m.cyTopHeight = 1
    m.cyBottomHeight = 1
    return DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(m))


class BrowserView:
    instances = {}

    app_menu_list = None

    class BrowserForm(WinForms.Form):
        def __init__(self, window, cache_dir):
            super().__init__()
            self.uid = window.uid
            self.pywebview_window = window
            self.pywebview_window.native = self
            self.real_url = None
            self.Text = window.title
            self.Size = Size(window.initial_width, window.initial_height)
            self.MinimumSize = Size(window.min_size[0], window.min_size[1])

            self.AutoScaleDimensions = SizeF(96.0, 96.0)
            self.AutoScaleMode = WinForms.AutoScaleMode.Dpi

            # for chromium edge, need this factor to modify the coordinates
            try:
                self.scale_factor = windll.shcore.GetScaleFactorForDevice(0) / 100 if is_chromium else 1
            except:
                self.scale_factor = 1

            if window.initial_x is not None and window.initial_y is not None:
                self.StartPosition = WinForms.FormStartPosition.Manual
                self.Location = Point(
                    int(window.initial_x * self.scale_factor),
                    int(window.initial_y * self.scale_factor)
                )
            elif window.screen:
                self.StartPosition = WinForms.FormStartPosition.Manual
                x = int(
                    window.screen.x * self.scale_factor + (window.screen.width - window.initial_width) * self.scale_factor / 2
                    if window.screen.x >= 0
                    else window.screen.X * self.scale_factor + window.screen.width / 2
                )
                y = int(window.screen.y * self.scale_factor + (window.screen.height - window.initial_height) * self.scale_factor / 2)
                self.Location = Point(x, y)
            else:
                self.StartPosition = WinForms.FormStartPosition.CenterScreen

            if not window.resizable:
                self.FormBorderStyle = WinForms.FormBorderStyle.FixedSingle
                self.MaximizeBox = False

            if window.maximized:
                self.WindowState = WinForms.FormWindowState.Maximized
            elif window.minimized:
                self.WindowState = WinForms.FormWindowState.Minimized

            self.old_state = self.WindowState

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
            self.TopMost = window.on_top

            self.is_fullscreen = False
            if window.fullscreen:
                self.toggle_fullscreen()

            if window.shadow:
                # Should do this before set frameless
                ExtendFrameIntoClientArea(self.Handle.ToInt32())
                DwmSetWindowAttribute(self.Handle.ToInt32(), 2, 2, 4)

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
                self.webview = self.browser.webview
            else:
                self.browser = IE.MSHTML(self, window, BrowserView.alert)
                self.webview = self.browser.webview

            if (
                window.transparent and self.browser
            ):  # window transparency is supported only with EdgeChromium
                self.BackColor = Color.FromArgb(255,255,0,0)
                self.TransparencyKey = Color.FromArgb(255,255,0,0)
                self.SetStyle(WinForms.ControlStyles.SupportsTransparentBackColor, True)
                self.browser.DefaultBackgroundColor = Color.Transparent
            else:
                self.BackColor = ColorTranslator.FromHtml(window.background_color)

            if not window.focus:
                windll.user32.SetWindowLongW(self.Handle.ToInt32(), -20, windll.user32.GetWindowLongW(self.Handle.ToInt32(), -20) | 0x8000000)

            self.Activated += self.on_activated
            self.Shown += self.on_shown
            self.FormClosed += self.on_close
            self.FormClosing += self.on_closing
            self.Resize += self.on_resize
            self.Move += self.on_move

            self.localization = window.localization

        def __str__(self):
            return f'<System.Windows.Forms object with {self.Handle} handle>'

        def on_activated(self, *_):
            if not self.pywebview_window.focus:
                windll.user32.SetWindowLongW(self.Handle.ToInt32(), -20, windll.user32.GetWindowLongW(self.Handle.ToInt32(), -20) | 0x8000000)

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

            self.pywebview_window.events.resized.set(self.Width, self.Height)

        def on_move(self, sender, args):
            self.pywebview_window.events.moved.set(self.Location.X, self.Location.Y)

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
                    valid_location = any(screen == self.old_screen for screen in WinForms.Screen.AllScreens)

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
            if self.scale_factor != 1:
                # The coordinates needed to be scaled
                x_modified = x * self.scale_factor
                y_modified = y * self.scale_factor
                windll.user32.SetWindowPos(
                    self.Handle.ToInt32(),
                    None,
                    int(x_modified),
                    int(y_modified),
                    None,
                    None,
                    SWP_NOSIZE | SWP_NOZORDER | SWP_SHOWWINDOW,
                )
            else:
                windll.user32.SetWindowPos(
                    self.Handle.ToInt32(),
                    None,
                    int(x),
                    int(y),
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

    @staticmethod
    def alert(message):
        WinForms.MessageBox.Show(str(message))


class OpenFolderDialog:
    foldersFilter = 'Folders|\n'
    flags = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic
    windowsFormsAssembly = Assembly.LoadWithPartialName('System.Windows.Forms')
    iFileDialogType = windowsFormsAssembly.GetType('System.Windows.Forms.FileDialogNative+IFileDialog')
    OpenFileDialogType = windowsFormsAssembly.GetType('System.Windows.Forms.OpenFileDialog')
    FileDialogType = windowsFormsAssembly.GetType('System.Windows.Forms.FileDialog')
    createVistaDialogMethodInfo = OpenFileDialogType.GetMethod('CreateVistaDialog', flags)
    onBeforeVistaDialogMethodInfo = OpenFileDialogType.GetMethod('OnBeforeVistaDialog', flags)
    getOptionsMethodInfo = FileDialogType.GetMethod('GetOptions', flags)
    setOptionsMethodInfo = iFileDialogType.GetMethod('SetOptions', flags)
    fosPickFoldersBitFlag = windowsFormsAssembly.GetType(
        'System.Windows.Forms.FileDialogNative+FOS').GetField('FOS_PICKFOLDERS').GetValue(None)

    vistaDialogEventsConstructorInfo = windowsFormsAssembly.GetType(
        'System.Windows.Forms.FileDialog+VistaDialogEvents').GetConstructor(flags, None, [FileDialogType], [])
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
        adviseParametersWithOutputConnectionToken = Array[Object]([
            OpenFolderDialog.vistaDialogEventsConstructorInfo.Invoke([openFileDialog]),
            UInt32(0),
        ])
        OpenFolderDialog.adviseMethodInfo.Invoke(iFileDialog, adviseParametersWithOutputConnectionToken)
        dwCookie = adviseParametersWithOutputConnectionToken.GetValue(1)
        try:
            result = OpenFolderDialog.showMethodInfo.Invoke(iFileDialog, [parent.Handle if parent else None])
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
        window.events.before_show.set()

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
        if is_chromium:
            init_storage()

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
        if dialog_type == FOLDER_DIALOG:
            file_path = OpenFolderDialog.show(i, directory, allow_multiple)

        elif dialog_type == OPEN_DIALOG:
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

        elif dialog_type == SAVE_DIALOG:
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
                file_path = dialog.FileName
            else:
                file_path = None

        return file_path
    except:
        logger.exception('Error invoking %s dialog', dialog_type)
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
        i.TopMost = on_top


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
        return i.Left, i.Top


def get_size(uid):
    i = BrowserView.instances.get(uid)
    if i:
        size = i.Size
        return size.Width, size.Height


def get_screens():
    screens = [Screen(s.Bounds.X, s.Bounds.Y, s.Bounds.Width, s.Bounds.Height, s.WorkingArea) for s in WinForms.Screen.AllScreens]
    return screens


def add_tls_cert(_):
    return
