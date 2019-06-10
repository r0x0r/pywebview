# -*- coding: utf-8 -*-

"""
(C) 2014-2019 Roman Sirokov and contributors
Licensed under BSD license

http://github.com/r0x0r/pywebview/
"""

import os
import sys 
import logging
import json
import webbrowser
from threading import Event, Semaphore
from ctypes import windll
from uuid import uuid4

from webview import WebViewException
from webview.util import parse_api_js, interop_dll_path, parse_file_type, inject_base_uri, default_html

import clr

clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Collections')
clr.AddReference('System.Threading')

import System.Windows.Forms as WinForms
from System import IntPtr, Int32, Func, Type, Environment, Uri
from System.Threading import Thread, ThreadStart, ApartmentState
from System.Drawing import Size, Point, Icon, Color, ColorTranslator, SizeF

from webview import OPEN_DIALOG, FOLDER_DIALOG, SAVE_DIALOG, _js_bridge_call, _debug

from webview.js import alert
from webview.js.css import disable_text_select

from webview.localization import localization

logger = logging.getLogger('pywebview')


is_cef = False
CEF = None

def use_cef():
    global CEF, is_cef
    from . import cef as CEF
    is_cef = True
    logger.debug('Using WinForms / CEF')


def _is_edge():
    windows_version = Environment.OSVersion.Version.Major, Environment.OSVersion.Version.Minor, Environment.OSVersion.Version.Build

    try:
        import _winreg as winreg  # Python 2
    except ImportError:
        import winreg  # Python 3

    try:
        net_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full')
        version, _ = winreg.QueryValueEx(net_key, 'Release')

        return version >= 394802 and windows_version >= (10, 0, 17134) # .NET 4.6.2 + Windows 10 1803 
    except:
        return False
    finally:
        winreg.CloseKey(net_key)

force_mshtml = os.environ['PYWEBVIEW_GUI'] and os.environ['PYWEBVIEW_GUI'].lower() == 'mshtml'
is_edge = _is_edge() and not force_mshtml


# TODO: Move this out of Edge initialization code
clr.AddReference(interop_dll_path('WebBrowserInterop.dll'))
from WebBrowserInterop import IWebBrowserInterop, WebBrowserEx

if is_edge:
    clr.AddReference(interop_dll_path('Microsoft.Toolkit.Forms.UI.Controls.WebView.dll'))
    from Microsoft.Toolkit.Forms.UI.Controls import WebView
    from System.ComponentModel import ISupportInitialize
    from Windows.Web import IUriToStreamResolver
    logger.debug('Using WinForms / EdgeHTML')
else:
    logger.debug('Using WinForms / MSHTML')



class BrowserView:
    instances = {}

    class MSHTML:
        class JSBridge(IWebBrowserInterop):
            __namespace__ = 'BrowserView.MSHTML.JSBridge'
            window = None

            def call(self, func_name, param):
                return _js_bridge_call(self.window, func_name, param)

            def alert(self, message):
                BrowserView.alert(message)

        def __init__(self, form, window):
            self.window = window
            self.web_browser = WebBrowserEx()
            self.web_browser.Dock = WinForms.DockStyle.Fill
            self.web_browser.ScriptErrorsSuppressed = not _debug
            self.web_browser.IsWebBrowserContextMenuEnabled = _debug
            self.web_browser.WebBrowserShortcutsEnabled = False
            self.web_browser.DpiAware = True

            self.web_browser.ScriptErrorsSuppressed = not _debug
            self.web_browser.IsWebBrowserContextMenuEnabled = _debug

            self.js_result_semaphore = Semaphore(0)
            self.js_bridge = BrowserView.MSHTML.JSBridge()
            self.js_bridge.window = window

            self.web_browser.ObjectForScripting = self.js_bridge

            # HACK. Hiding the WebBrowser is needed in order to show a non-default background color. Tweaking the Visible property
            # results in showing a non-responsive control, until it is loaded fully. To avoid this, we need to disable this behaviour
            # for the default background color.
            if window.background_color != '#FFFFFF':
                self.web_browser.Visible = False
                self.first_load = True
            else:
                self.first_load = False

            self.cancel_back = False
            self.web_browser.PreviewKeyDown += self.on_preview_keydown
            self.web_browser.Navigating += self.on_navigating
            self.web_browser.NewWindow3 += self.on_new_window
            self.web_browser.DownloadComplete += self.on_download_complete
            self.web_browser.DocumentCompleted += self.on_document_completed
            
            if window.url:
                self.web_browser.Navigate(window.url)
            elif window.html:
                self.web_browser.DocumentText = window.html
            else:
                self.web_browser.DocumentText = default_html

            form.Controls.Add(self.web_browser)

        def evaluate_js(self, script):
            result = self.web_browser.Document.InvokeScript('eval', (script,))
            self.js_result = None if result is None or result is 'null' else json.loads(result)
            self.js_result_semaphore.release()

        def load_html(self, content, base_uri):
            self.web_browser.DocumentText = inject_base_uri(content, base_uri)
            self.window.loaded.clear()

        def load_url(self, url):
            self.web_browser.Navigate(url)

        def on_preview_keydown(self, sender, args):
            if args.KeyCode == WinForms.Keys.Back:
                self.cancel_back = True
            elif args.KeyCode == WinForms.Keys.Delete:
                self.web_browser.Document.ExecCommand('Delete', False, None)
            elif args.Modifiers == WinForms.Keys.Control and args.KeyCode == WinForms.Keys.C:
                self.web_browser.Document.ExecCommand('Copy', False, None)
            elif args.Modifiers == WinForms.Keys.Control and args.KeyCode == WinForms.Keys.X:
                self.web_browser.Document.ExecCommand('Cut', False, None)
            elif args.Modifiers == WinForms.Keys.Control and args.KeyCode == WinForms.Keys.V:
                self.web_browser.Document.ExecCommand('Paste', False, None)
            elif args.Modifiers == WinForms.Keys.Control and args.KeyCode == WinForms.Keys.Z:
                self.web_browser.Document.ExecCommand('Undo', False, None)
            elif args.Modifiers == WinForms.Keys.Control and args.KeyCode == WinForms.Keys.A:
                self.web_browser.Document.ExecCommand('selectAll', False, None)

        def on_new_window(self, sender, args):
            args.Cancel = True
            webbrowser.open(args.Url)

        def on_download_complete(self, sender, args):
            pass

        def on_navigating(self, sender, args):
            if self.cancel_back:
                args.Cancel = True
                self.cancel_back = False

        def on_document_completed(self, sender, args):
            self.web_browser.Document.InvokeScript('eval', (alert.src,))

            if self.first_load:
                self.web_browser.Visible = True
                self.first_load = False

            self.url = None if args.Url.AbsoluteUri == 'about:blank' else str(args.Url.AbsoluteUri)

            document = self.web_browser.Document
            document.InvokeScript('eval', (parse_api_js(self.js_bridge.window.js_api),))

            if not self.window.text_select:
                document.InvokeScript('eval', (disable_text_select,))
            
            self.window.loaded.set()

            if self.frameless:
                document.MouseMove += self.on_mouse_move

        def on_mouse_move(self, sender, e):
            if e.MouseButtonsPressed == WinForms.MouseButtons.Left:
                WebBrowserEx.ReleaseCapture()
                WebBrowserEx.SendMessage(self.Handle, WebBrowserEx.WM_NCLBUTTONDOWN, WebBrowserEx.HT_CAPTION, 0)

    class EdgeHTML:
        def __init__(self, form, window):
            print('edge htmll')
            self.window = window
            self.web_view = WebView()
            
            life = ISupportInitialize(self.web_view)
            life.BeginInit()
            form.Controls.Add(self.web_view)

            self.js_result_semaphore = Semaphore(0)
            self.web_view.Dock = WinForms.DockStyle.Fill
            self.web_view.DpiAware = True
            self.web_view.IsIndexedDBEnabled = True
            self.web_view.IsJavaScriptEnabled = True
            self.web_view.IsScriptNotifyAllowed = True
            self.web_view.DefaultBackgroundColor = form.BackColor

            self.web_view.ScriptNotify += self.on_script_notify
            self.web_view.NewWindowRequested += self.on_new_window_request
            self.web_view.NavigationStarting += self.on_navigation_started
            self.web_view.NavigationCompleted += self.on_navigation_completed
            self.web_view.UnviewableContentIdentified += self.on_unviewable_content_identified

            # This must be before loading URL. Otherwise the webview will remain empty
            life.EndInit()

            self.temp_html = None

            if window.url:
                self.load_url(window.url)
            elif window.html:
                self.load_html(window.html, '')
            else:
                self.load_html(default_html, '')

        def evaluate_js(self, script):
            result = self.web_view.InvokeScript('eval', (script,))
            self.js_result = None if result is None or result == '' else json.loads(result)
            self.js_result_semaphore.release()

        def get_current_url():
            return self.url

        def load_html(self, html, base_uri):
            file_name = '%s.html' % uuid4().hex
            self.temp_html = os.path.join(WinForms.Application.StartupPath, file_name)

            with open(self.temp_html, 'w') as f:
                f.write(inject_base_uri(html, base_uri))
            
            self.web_view.NavigateToLocal(file_name)

        def load_url(self, url):
            self.temp_html = None

            # WebViewControl as of 5.1.1 crashes on file:// urls. Stupid workaround to make it work
            if url.startswith('file://'):
                path = url.replace('file://', '')

                if not os.path.exists(path):
                    raise WebViewException('File %s does not exist' % path)

                with open(path) as f:
                    html = f.read()
                    self.load_html(html, 'file://' + os.path.dirname(path) + '\\')
                
            else:
                self.web_view.Navigate(url)

        def on_script_notify(self, _, args):
            func_name, func_param = json.loads(args.Value)

            if func_name == 'alert':
                WinForms.MessageBox.Show(func_param)
            elif func_name == 'console':
                print(func_param)
            else:
                _js_bridge_call(self.window, func_name, func_param)

        def on_new_window_request(self, _, args):
            webbrowser.open(str(args.get_Uri()))
            args.set_Handled(True)

        def on_navigation_started(self, _, args):
            if self.window.js_api:
                self.web_view.AddInitializeScript(parse_api_js(self.window.js_api))

            if not self.window.text_select:
                self.web_view.AddInitializeScript(disable_text_select)

        def on_navigation_completed(self, _, args):
            try:
                if self.temp_html and os.path.exists(self.temp_html):
                    os.remove(self.temp_html)
                    self.temp_html = None
            except Exception as e:
                logger.exception('Failed deleting %s' % self.temp_html)

            self.web_view.InvokeScriptAsync('eval', ('window.alert = (msg) => window.external.notify(JSON.stringify(["alert", msg+""]))',))

            if _debug:
                self.web_view.InvokeScriptAsync('eval', ('window.console = { log: (msg) => window.external.notify(JSON.stringify(["console", msg+""]))}',))
            
            if self.window.js_api:
                self.web_view.InvokeScriptAsync('eval', (parse_api_js(self.window.js_api),))

            if not self.window.text_select:
                self.web_view.InvokeScriptAsync('eval', (disable_text_select,))

            self.window.loaded.set()

        def on_unviewable_content_identified(self, _, args):
            # TODO: Use this to implement download
            print(args.get_MediaType(), args.get_Uri())

    class BrowserForm(WinForms.Form):
        def __init__(self, window):
            self.uid = window.uid
            self.real_url = None
            self.Text = window.title
            self.ClientSize = Size(window.width, window.height)
            self.MinimumSize = Size(window.min_size[0], window.min_size[1])
            self.BackColor = ColorTranslator.FromHtml(window.background_color)

            self.AutoScaleDimensions = SizeF(96.0, 96.0)
            self.AutoScaleMode = WinForms.AutoScaleMode.Dpi

            if not window.resizable:
                self.FormBorderStyle = WinForms.FormBorderStyle.FixedSingle
                self.MaximizeBox = False

            # Application icon
            handle = windll.kernel32.GetModuleHandleW(None)
            icon_handle = windll.shell32.ExtractIconW(handle, sys.executable, 0)

            if icon_handle != 0:
                self.Icon = Icon.FromHandle(IntPtr.op_Explicit(Int32(icon_handle))).Clone()

            windll.user32.DestroyIcon(icon_handle)

            self.shown = window.shown
            self.loaded = window.loaded
            self.url = window.url
            self.text_select = window.text_select

            self.is_fullscreen = False
            if window.fullscreen:
                self.toggle_fullscreen()

            if window.frameless:
                self.frameless = window.frameless
                self.FormBorderStyle = 0

            if is_cef:
                CEF.create_browser(window, self.Handle.ToInt32(), BrowserView.alert)
            elif is_edge:
                self.browser = BrowserView.EdgeHTML(self, window)
            else:
                self.browser = BrowserView.MSHTML(self, window)
  

            self.Shown += self.on_shown
            self.FormClosed += self.on_close

            if is_cef:
                self.Resize += self.on_resize

            if window.confirm_close:
                self.FormClosing += self.on_closing

        def on_shown(self, sender, args):
            if not is_cef:
                self.shown.set()

        def on_close(self, sender, args):
            def _shutdown():
                if is_cef:
                    CEF.shutdown()
                WinForms.Application.Exit()

            if is_cef:
                CEF.close_window(self.uid)

            del BrowserView.instances[self.uid]

            if len(BrowserView.instances) == 0:
                self.Invoke(Func[Type](_shutdown))

        def on_closing(self, sender, args):
            result = WinForms.MessageBox.Show(localization['global.quitConfirmation'], self.Text,
                                              WinForms.MessageBoxButtons.OKCancel, WinForms.MessageBoxIcon.Asterisk)

            if result == WinForms.DialogResult.Cancel:
                args.Cancel = True

        def on_resize(self, sender, args):
            CEF.resize(self.Width, self.Height, self.uid)

        def evaluate_js(self, script):
            def _evaluate_js():
                self.browser.evaluate_js(script)

            self.Invoke(Func[Type](_evaluate_js))
            self.browser.js_result_semaphore.acquire()

            return self.browser.js_result

        def load_html(self, content, base_uri):
            def _load_html():
                 self.browser.load_html(content, base_uri)

            self.Invoke(Func[Type](_load_html))

        def load_url(self, url):
            def _load_url():
                self.browser.load_url(url)

            self.Invoke(Func[Type](_load_url))

        def get_current_url(self):
            return self.browser.get_current_url

        def toggle_fullscreen(self):
            def _toggle():
                screen = WinForms.Screen.FromControl(self)
                if not self.is_fullscreen:
                    self.old_size = self.Size
                    self.old_state = self.WindowState
                    self.old_style = self.FormBorderStyle
                    self.old_location = self.Location
                    self.TopMost = True
                    self.FormBorderStyle = 0  # FormBorderStyle.None
                    self.Bounds = WinForms.Screen.PrimaryScreen.Bounds
                    self.WindowState = WinForms.FormWindowState.Maximized
                    self.is_fullscreen = True
                    windll.user32.SetWindowPos(self.Handle.ToInt32(), None, screen.Bounds.X, screen.Bounds.Y,
                                            screen.Bounds.Width, screen.Bounds.Height, 64)
                else:
                    self.TopMost = False
                    self.Size = self.old_size
                    self.WindowState = self.old_state
                    self.FormBorderStyle = self.old_style
                    self.Location = self.old_location
                    self.is_fullscreen = False

            if self.InvokeRequired:
                self.Invoke(Func[Type](_toggle))

        def set_window_size(self, width, height):
            windll.user32.SetWindowPos(self.Handle.ToInt32(), None, self.Location.X, self.Location.Y,
                width, height, 64)

    @staticmethod
    def alert(message):
        WinForms.MessageBox.Show(message)


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
        browser.Show()

        _main_window_created.set()

        if window.uid == 'master':
            app.Run()

    app = WinForms.Application

    if window.uid == 'master':
        if not is_edge and not is_cef:
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
                dialog.Filter = localization['windows.fileFilter.allFiles'] + ' (*.*)|*.*'
            dialog.RestoreDirectory = True

            result = dialog.ShowDialog(window)
            if result == WinForms.DialogResult.OK:
                file_path = tuple(dialog.FileNames)
            else:
                file_path = None

        elif dialog_type == SAVE_DIALOG:
            dialog = WinForms.SaveFileDialog()
            dialog.Filter = localization['windows.fileFilter.allFiles'] + ' (*.*)|'
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


def toggle_fullscreen(uid):
    window = BrowserView.instances[uid]
    window.toggle_fullscreen()


def set_window_size(width, height, uid):
    window = BrowserView.instances[uid]
    window.set_window_size(width, height)


def destroy_window(uid):
    def _close():
        window.Close()

    window = BrowserView.instances[uid]
    window.Invoke(Func[Type](_close))

    if not is_cef:
        window.browser.js_result_semaphore.release()


def evaluate_js(script, uid):
    if is_cef:
        return CEF.evaluate_js(script, uid)
    else:
        return BrowserView.instances[uid].evaluate_js(script)

