import json
import logging
import sys
import webbrowser
import winreg
from ctypes import windll
from threading import Semaphore
from time import sleep

import clr

from webview import _settings
from webview.util import (DEFAULT_HTML, inject_base_uri, interop_dll_path, js_bridge_call,
                          inject_pywebview)

clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Collections')
clr.AddReference('System.Threading')

import System.Windows.Forms as WinForms

clr.AddReference(interop_dll_path('WebBrowserInterop.dll'))
from WebBrowserInterop import IWebBrowserInterop, WebBrowserEx

logger = logging.getLogger('pywebview')
settings = {}

renderer = 'mshtml'

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
        ie_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'Software\Microsoft\Internet Explorer')
        try:
            version, _ = winreg.QueryValueEx(ie_key, 'svcVersion')
        except:
            version, _ = winreg.QueryValueEx(ie_key, 'Version')

        winreg.CloseKey(ie_key)

        if version.startswith('11'):
            value = 0x2AF9
        elif version.startswith('10'):
            value = 0x2711
        elif version.startswith('9'):
            value = 0x270F
        elif version.startswith('8'):
            value = 0x22B8
        else:
            value = 0x2AF9  # Set IE11 as default

        return value

    try:
        browser_emulation = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Internet Explorer\Main\FeatureControl\FEATURE_BROWSER_EMULATION',
            0,
            winreg.KEY_ALL_ACCESS,
        )
    except WindowsError:
        browser_emulation = winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Internet Explorer\Main\FeatureControl\FEATURE_BROWSER_EMULATION',
            0,
            winreg.KEY_ALL_ACCESS,
        )

    try:
        dpi_support = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Internet Explorer\Main\FeatureControl\FEATURE_96DPI_PIXEL',
            0,
            winreg.KEY_ALL_ACCESS,
        )
    except WindowsError:
        dpi_support = winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Internet Explorer\Main\FeatureControl\FEATURE_96DPI_PIXEL',
            0,
            winreg.KEY_ALL_ACCESS,
        )

    mode = get_ie_mode()
    executable_name = sys.executable.split('\\')[-1]
    winreg.SetValueEx(browser_emulation, executable_name, 0, winreg.REG_DWORD, mode)
    winreg.CloseKey(browser_emulation)

    winreg.SetValueEx(dpi_support, executable_name, 0, winreg.REG_DWORD, 1)
    winreg.CloseKey(dpi_support)


class MSHTML:
    alert = None

    class JSBridge(IWebBrowserInterop):
        __namespace__ = 'MSHTML.JSBridge'
        window = None

        def call(self, func_name, param, value_id):
            print(func_name, param)
            return js_bridge_call(self.window, func_name, json.loads(param), value_id)

        def alert(self, message):
            MSHTML.alert(str(message))

        def console(self, message):
            print(message)

    def __init__(self, form, window, alert):
        self.pywebview_window = window
        self.webview = WebBrowserEx()
        self.webview.Dock = WinForms.DockStyle.Fill
        self.webview.ScriptErrorsSuppressed = not _settings['debug']
        self.webview.IsWebBrowserContextMenuEnabled = _settings['debug']
        self.webview.WebBrowserShortcutsEnabled = False
        self.webview.DpiAware = True
        MSHTML.alert = alert

        user_agent = _settings['user_agent'] or settings.get('user_agent')
        if user_agent:
            self.webview.ChangeUserAgent(user_agent)

        self.webview.ScriptErrorsSuppressed = not _settings['debug']
        self.webview.IsWebBrowserContextMenuEnabled = _settings['debug']

        self.js_result_semaphore = Semaphore(0)
        self.js_bridge = MSHTML.JSBridge()
        self.js_bridge.window = window

        self.webview.ObjectForScripting = self.js_bridge

        # HACK. Hiding the WebBrowser is needed in order to show a non-default background color. Tweaking the Visible property
        # results in showing a non-responsive control, until it is loaded fully. To avoid this, we need to disable this behaviour
        # for the default background color.
        if window.background_color != '#FFFFFF':
            self.webview.Visible = False
            self.first_load = True
        else:
            self.first_load = False

        self.cancel_back = False
        self.webview.PreviewKeyDown += self.on_preview_keydown
        self.webview.Navigating += self.on_navigating
        self.webview.NewWindow3 += self.on_new_window
        self.webview.DownloadComplete += self.on_download_complete
        self.webview.DocumentCompleted += self.on_document_completed

        if window.real_url:
            self.webview.Navigate(window.real_url)
        elif window.html:
            self.webview.DocumentText = window.html
        else:
            self.webview.DocumentText = DEFAULT_HTML

        self.form = form
        form.Controls.Add(self.webview)

    def evaluate_js(self, script):
        result = self.webview.Document.InvokeScript('eval', (script,))
        self.js_result = None if result is None or result == 'null' else json.loads(result)  ##
        self.js_result_semaphore.release()

    def load_html(self, content, base_uri):
        self.webview.DocumentText = inject_base_uri(content, base_uri)
        self.pywebview_window.events.loaded.clear()

    def load_url(self, url):
        self.webview.Navigate(url)

    def on_preview_keydown(self, _, args):
        if args.KeyCode == WinForms.Keys.Back:
            self.cancel_back = True
        elif args.KeyCode == WinForms.Keys.Delete:
            self.webview.Document.ExecCommand('Delete', False, None)
        elif args.Modifiers == WinForms.Keys.Control and args.KeyCode == WinForms.Keys.C:
            self.webview.Document.ExecCommand('Copy', False, None)
        elif args.Modifiers == WinForms.Keys.Control and args.KeyCode == WinForms.Keys.X:
            self.webview.Document.ExecCommand('Cut', False, None)
        elif args.Modifiers == WinForms.Keys.Control and args.KeyCode == WinForms.Keys.V:
            self.webview.Document.ExecCommand('Paste', False, None)
        elif args.Modifiers == WinForms.Keys.Control and args.KeyCode == WinForms.Keys.Z:
            self.webview.Document.ExecCommand('Undo', False, None)
        elif args.Modifiers == WinForms.Keys.Control and args.KeyCode == WinForms.Keys.A:
            self.webview.Document.ExecCommand('selectAll', False, None)

    def on_new_window(self, sender, args):
        args.Cancel = True
        webbrowser.open(args.Url)

    def on_download_complete(self, *_):
        pass

    def on_navigating(self, _, args):
        if self.cancel_back:
            args.Cancel = True
            self.cancel_back = False

    def on_document_completed(self, _, args):
        document = self.webview.Document

        if _settings['debug']:
            document.InvokeScript(
                'eval', """
                    window.console = {
                        log: function(msg) { window.external.console(JSON.stringify(msg)) },
                        error: function(msg) { window.external.console(JSON.stringify(msg)) }
                    }',
                """
            )

        if self.first_load:
            self.webview.Visible = True
            self.first_load = False

        self.url = None if args.Url.AbsoluteUri == 'about:blank' else str(args.Url.AbsoluteUri)

        document.InvokeScript('eval', (inject_pywebview(self.pywebview_window, renderer),))
        sleep(0.1)
        self.pywebview_window.events.loaded.set()

        if self.pywebview_window.easy_drag:
            document.MouseMove += self.on_mouse_move

    def on_mouse_move(self, _, e):
        if e.MouseButtonsPressed == WinForms.MouseButtons.Left:
            WebBrowserEx.ReleaseCapture()
            windll.user32.SendMessageW(
                self.form.Handle.ToInt32(),
                WebBrowserEx.WM_NCLBUTTONDOWN,
                WebBrowserEx.HT_CAPTION,
                6,
            )
