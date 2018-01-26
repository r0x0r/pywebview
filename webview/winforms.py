# -*- coding: utf-8 -*-

"""
(C) 2014-2016 Roman Sirokov and contributors
Licensed under BSD license

http://github.com/r0x0r/pywebview/
"""

import os
import sys
import logging
import threading
from ctypes import windll

base_dir = os.path.dirname(os.path.realpath(__file__))

import clr
clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Threading')
clr.AddReference(os.path.join(base_dir, 'lib', 'WebBrowserInterop.dll'))
import System.Windows.Forms as WinForms

from System import IntPtr, Int32, Func, Type #, EventHandler
from System.Threading import Thread, ThreadStart, ApartmentState
from System.Drawing import Size, Point, Icon, Color, ColorTranslator
from WebBrowserInterop import IWebBrowserInterop

from webview import OPEN_DIALOG, FOLDER_DIALOG, SAVE_DIALOG
from webview import _parse_file_type, _parse_api_js, _js_bridge_call

from webview.localization import localization
from webview.win32_shared import set_ie_mode


logger = logging.getLogger(__name__)


class BrowserView:

    class JSBridge(IWebBrowserInterop):
        __namespace__ = 'BrowserView.JSBridge'
        api = None

        def call(self, func_name, param):
            return _js_bridge_call(self.api, func_name, param)

        def alert(self, message):
            if message:
                WinForms.MessageBox.Show(message)

    class BrowserForm(WinForms.Form):
        def __init__(self, title, url, width, height, resizable, fullscreen, min_size,
                     confirm_quit, background_color, debug, js_api, webview_ready):
            self.Text = title
            self.ClientSize = Size(width, height)
            self.MinimumSize = Size(min_size[0], min_size[1])
            self.BackColor = ColorTranslator.FromHtml(background_color)

            if not resizable:
                self.FormBorderStyle = WinForms.FormBorderStyle.FixedSingle
                self.MaximizeBox = False

            # Application icon
            handle = windll.kernel32.GetModuleHandleW(None)
            icon_handle = windll.shell32.ExtractIconW(handle, sys.executable, 0)

            if icon_handle != 0:
                self.Icon = Icon.FromHandle(IntPtr.op_Explicit(Int32(icon_handle))).Clone()

            windll.user32.DestroyIcon(icon_handle)

            self.webview_ready = webview_ready

            self.web_browser = WinForms.WebBrowser()
            self.web_browser.Dock = WinForms.DockStyle.Fill
            self.web_browser.ScriptErrorsSuppressed = False
            self.web_browser.IsWebBrowserContextMenuEnabled = False
            self.web_browser.WebBrowserShortcutsEnabled = False

            self.js_bridge = BrowserView.JSBridge()
            self.web_browser.ObjectForScripting = self.js_bridge

            if js_api:
                self.js_bridge.api = js_api

            # HACK. Hiding the WebBrowser is needed in order to show a non-default background color. Tweaking the Visible property
            # results in showing a non-responsive control, until it is loaded fully. To avoid this, we need to disable this behaviour
            # for the default background color.
            if background_color != '#FFFFFF':
                self.web_browser.Visible = False
                self.first_load = True
            else:
                self.first_load = False

            self.cancel_back = False
            self.web_browser.PreviewKeyDown += self.on_preview_keydown
            self.web_browser.Navigating += self.on_navigating
            self.web_browser.DocumentCompleted += self.on_document_completed
            if url:
                self.web_browser.Navigate(url)

            self.Controls.Add(self.web_browser)
            self.is_fullscreen = False
            self.Shown += self.on_shown

            if confirm_quit:
                self.FormClosing += self.on_closing

            if fullscreen:
                self.toggle_fullscreen()

        def _initialize_js(self):
            with open(os.path.join(base_dir, 'js', 'alert.js')) as f:
                self.web_browser.Document.InvokeScript('eval', (f.read(),))

        def on_shown(self, sender, args):
            self.webview_ready.set()

        def on_closing(self, sender, args):
            result = WinForms.MessageBox.Show(localization['global.quitConfirmation'], self.Text,
                                              WinForms.MessageBoxButtons.OKCancel, WinForms.MessageBoxIcon.Asterisk)

            if result == WinForms.DialogResult.Cancel:
                args.Cancel = True

        def on_preview_keydown(self, sender, args):
            if args.KeyCode == WinForms.Keys.Back:
                self.cancel_back = True
            elif args.KeyCode == WinForms.Keys.Delete:
                self.web_browser.Document.ExecCommand("Delete", False, None)
            elif args.Modifiers == WinForms.Keys.Control and args.KeyCode == WinForms.Keys.C:
                self.web_browser.Document.ExecCommand("Copy", False, None)
            elif args.Modifiers == WinForms.Keys.Control and args.KeyCode == WinForms.Keys.X:
                self.web_browser.Document.ExecCommand("Cut", False, None)
            elif args.Modifiers == WinForms.Keys.Control and args.KeyCode == WinForms.Keys.V:
                self.web_browser.Document.ExecCommand("Paste", False, None)
            elif args.Modifiers == WinForms.Keys.Control and args.KeyCode == WinForms.Keys.Z:
                self.web_browser.Document.ExecCommand("Undo", False, None)
            elif args.Modifiers == WinForms.Keys.Control and args.KeyCode == WinForms.Keys.A:
                self.web_browser.Document.ExecCommand("selectAll", False, None)

        def on_navigating(self, sender, args):
            if self.cancel_back:
                args.Cancel = True
                self.cancel_back = False

        def on_document_completed(self, sender, args):
            self._initialize_js()
            BrowserView.instance.load_event.set()

            if self.first_load:
                self.web_browser.Visible = True
                self.first_load = False

            if self.js_bridge.api:
                document = self.web_browser.Document
                document.InvokeScript('eval', (_parse_api_js(self.js_bridge.api),))

        def toggle_fullscreen(self):
            if not self.is_fullscreen:
                self.old_size = self.Size
                self.old_state = self.WindowState
                self.old_style = self.FormBorderStyle
                self.old_location = self.Location

                screen = WinForms.Screen.FromControl(self)

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

    instance = None
    load_event = threading.Event()

    def __init__(self, title, url, width, height, resizable, fullscreen, min_size, confirm_quit, background_color, debug, js_api, webview_ready):
        BrowserView.instance = self
        self.title = title
        self.url = url
        self.width = width
        self.height = height
        self.resizable = resizable
        self.fullscreen = fullscreen
        self.min_size = min_size
        self.confirm_quit = confirm_quit
        self.webview_ready = webview_ready
        self.background_color = background_color
        self.debug = debug
        self.js_api = js_api
        self.browser = None
        self._js_result_semaphor = threading.Semaphore(0)

    def show(self):
        def start():
            app = WinForms.Application
            self.browser = BrowserView.BrowserForm(self.title, self.url, self.width,self.height, self.resizable,
                                                   self.fullscreen, self.min_size, self.confirm_quit, self.background_color, 
                                                   self.debug, self.js_api, self.webview_ready)

            app.Run(self.browser)

        thread = Thread(ThreadStart(start))
        thread.SetApartmentState(ApartmentState.STA)
        thread.Start()
        thread.Join()

    def destroy(self):
        self.browser.Close()
        self._js_result_semaphor.release()

    def get_current_url(self):
        return self.browser.web_browser.Url.AbsoluteUri

    def load_url(self, url):
        self.load_event.clear()
        self.url = url
        self.browser.web_browser.Navigate(url)

    def load_html(self, content):
        def _load_html():
            self.browser.web_browser.DocumentText = content

        self.load_event.clear()

        if self.browser.web_browser.InvokeRequired:
            self.browser.web_browser.Invoke(Func[Type](_load_html))
        else:
            _load_html()

    def create_file_dialog(self, dialog_type, directory, allow_multiple, save_filename, file_types):
        if not directory:
            directory = os.environ['HOMEPATH']

        try:
            if dialog_type == FOLDER_DIALOG:
                dialog = WinForms.FolderBrowserDialog()
                dialog.RestoreDirectory = True

                result = dialog.ShowDialog(BrowserView.instance.browser)
                if result == WinForms.DialogResult.OK:
                    file_path = (dialog.SelectedPath,)
                else:
                    file_path = None
            elif dialog_type == OPEN_DIALOG:
                dialog = WinForms.OpenFileDialog()

                dialog.Multiselect = allow_multiple
                dialog.InitialDirectory = directory

                if len(file_types) > 0:
                    dialog.Filter = '|'.join(['{0} ({1})|{1}'.format(*_parse_file_type(f)) for f in file_types])
                else:
                    dialog.Filter = localization['windows.fileFilter.allFiles'] + ' (*.*)|*.*'
                dialog.RestoreDirectory = True

                result = dialog.ShowDialog(BrowserView.instance.browser)
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

                result = dialog.ShowDialog(BrowserView.instance.browser)
                if result == WinForms.DialogResult.OK:
                    file_path = dialog.FileName
                else:
                    file_path = None

            return file_path

        except:
            logger.exception('Error invoking {0} dialog'.format(dialog_type))
            return None

    def toggle_fullscreen(self):
        self.browser.toggle_fullscreen()

    def evaluate_js(self, script):
        def _evaluate_js():
            document = self.browser.web_browser.Document
            self._js_result = document.InvokeScript('eval', (script,))
            self._js_result_semaphor.release()

        self.load_event.wait()
        if self.browser.web_browser.InvokeRequired:
            self.browser.web_browser.Invoke(Func[Type](_evaluate_js))
        else:
            _evaluate_js()

        self._js_result_semaphor.acquire()

        return self._js_result


def create_window(uid, title, url, width, height, resizable, fullscreen, min_size,
                  confirm_quit, background_color, debug, js_api, webview_ready):
    set_ie_mode()
    browser_view = BrowserView(title, url, width, height, resizable, fullscreen,
                               min_size, confirm_quit, background_color, debug, js_api, webview_ready)
    browser_view.show()


def create_file_dialog(dialog_type, directory, allow_multiple, save_filename, file_types):
    return BrowserView.instance.create_file_dialog(dialog_type, directory, allow_multiple, save_filename, file_types)


def get_current_url(uid):
    return BrowserView.instance.get_current_url()


def load_url(url, uid):
    BrowserView.instance.load_url(url)


def load_html(content, base_uri, uid):
    BrowserView.instance.load_html(content)


def toggle_fullscreen(uid):
    BrowserView.instance.toggle_fullscreen()


def destroy_window(uid):
    BrowserView.instance.destroy()


def evaluate_js(script, uid):
    return BrowserView.instance.evaluate_js(script)
