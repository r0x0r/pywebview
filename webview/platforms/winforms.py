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

import clr

clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Threading')

import System.Windows.Forms as WinForms
from System import IntPtr, Int32, Func, Type, Environment
from System.Threading import Thread, ThreadStart, ApartmentState
from System.Drawing import Size, Point, Icon, Color, ColorTranslator, SizeF

from webview import OPEN_DIALOG, FOLDER_DIALOG, SAVE_DIALOG, _js_bridge_call, config, _debug
from webview.util import parse_api_js, interop_dll_path, parse_file_type, inject_base_uri, default_html

from webview.js import alert
from webview.js.css import disable_text_select
from webview.logger import logger

from webview.localization import localization
from webview.win32_shared import set_ie_mode

clr.AddReference(interop_dll_path())
from WebBrowserInterop import IWebBrowserInterop, WebBrowserEx

is_cef = config.gui == 'cef'

if is_cef:
    from . import cef as CEF


class BrowserView:
    instances = {}

    class JSBridge(IWebBrowserInterop):
        __namespace__ = 'BrowserView.JSBridge'
        window = None

        def call(self, func_name, param):
            return _js_bridge_call(self.window, func_name, param)

        def alert(self, message):
            BrowserView.alert(message)

    class BrowserForm(WinForms.Form):
        def __init__(self, window):
            self.uid = window.uid
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
            self.background_color = window.background_color
            self.url = window.url

            self.is_fullscreen = False
            if window.fullscreen:
                self.toggle_fullscreen()

            if window.frameless:
                self.frameless = window.frameless
                self.FormBorderStyle = 0

            if is_cef:
                CEF.create_browser(window, self.Handle.ToInt32(), BrowserView.alert)
            else:
                self._create_mshtml_browser(window)

            self.text_select = window.text_select
            self.Shown += self.on_shown
            self.FormClosed += self.on_close

            if is_cef:
                self.Resize += self.on_resize

            if window.confirm_close:
                self.FormClosing += self.on_closing

        def _create_mshtml_browser(self, window):
            self.web_browser = WebBrowserEx()
            self.web_browser.Dock = WinForms.DockStyle.Fill
            self.web_browser.ScriptErrorsSuppressed = not _debug
            self.web_browser.IsWebBrowserContextMenuEnabled = _debug
            self.web_browser.WebBrowserShortcutsEnabled = False
            self.web_browser.DpiAware = True

            self.web_browser.ScriptErrorsSuppressed = not _debug
            self.web_browser.IsWebBrowserContextMenuEnabled = _debug

            self.js_result_semaphore = Semaphore(0)
            self.js_bridge = BrowserView.JSBridge()
            self.js_bridge.window = window

            self.web_browser.ObjectForScripting = self.js_bridge

            # HACK. Hiding the WebBrowser is needed in order to show a non-default background color. Tweaking the Visible property
            # results in showing a non-responsive control, until it is loaded fully. To avoid this, we need to disable this behaviour
            # for the default background color.
            if self.background_color != '#FFFFFF':
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
            else:
                self.web_browser.DocumentText = default_html

            self.Controls.Add(self.web_browser)

        def _initialize_js(self):
            self.web_browser.Document.InvokeScript('eval', (alert.src,))

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
            document = self.web_browser.Document

            if self.js_bridge.window.api:
                document.InvokeScript('eval', (parse_api_js(self.js_bridge.window.api),))

            if not self.text_select:
                document.InvokeScript('eval', (disable_text_select,))

        def on_navigating(self, sender, args):
            if self.cancel_back:
                args.Cancel = True
                self.cancel_back = False

        def on_document_completed(self, sender, args):
            self._initialize_js()

            if self.first_load:
                self.web_browser.Visible = True
                self.first_load = False

            self.loaded.set()

            if self.frameless:
                self.web_browser.Document.MouseMove += self.on_mouse_move

        def on_mouse_move(self, sender, e):
            if e.MouseButtonsPressed == WinForms.MouseButtons.Left:
                WebBrowserEx.ReleaseCapture()
                WebBrowserEx.SendMessage(self.Handle, WebBrowserEx.WM_NCLBUTTONDOWN, WebBrowserEx.HT_CAPTION, 0)


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


def create_window(window):
    def create():
        browser = BrowserView.BrowserForm(window)
        BrowserView.instances[window.uid] = browser
        browser.Show()

        if window.uid == 'master':
            app.Run()

    # webview_ready.clear() TODO
    app = WinForms.Application

    if window.uid == 'master':
        set_ie_mode()
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

        if window.url is None:
            return None
        else:
            window.loaded.wait()
            return window.web_browser.Url.AbsoluteUri


def load_url(url, uid):
    def _load_url():
        window.url = url
        window.web_browser.Navigate(url)

    window = BrowserView.instances[uid]
    window.loaded.clear()

    if is_cef:
        CEF.load_url(url, uid)
    elif window.web_browser.InvokeRequired:
        window.web_browser.Invoke(Func[Type](_load_url))
    else:
        _load_url()


def load_html(content, base_uri, uid):
    def _load_html():
        window.web_browser.DocumentText = inject_base_uri(content, base_uri)

    if is_cef:
        CEF.load_html(inject_base_uri(content, base_uri), uid)
        return

    window = BrowserView.instances[uid]
    window.loaded.clear()

    if window.InvokeRequired:
        window.Invoke(Func[Type](_load_html))
    else:
        _load_html()


def toggle_fullscreen(uid):
    window = BrowserView.instances[uid]
    window.toggle_fullscreen()


def set_window_size(width, height, uid):
    window = BrowserView.instances[uid]
    window.set_window_size(width, height)


def destroy_window(uid):
    window = BrowserView.instances[uid]
    window.Close()

    if not is_cef:
        window.js_result_semaphore.release()


def evaluate_js(script, uid):
    def _evaluate_js():
        document = window.web_browser.Document

        result = document.InvokeScript('eval', (script,))
        window.js_result = None if result is None or result is 'null' else json.loads(result)
        window.js_result_semaphore.release()

    if is_cef:
        return CEF.evaluate_js(script, uid)
    else:
        window = BrowserView.instances[uid]
        window.loaded.wait()
        window.Invoke(Func[Type](_evaluate_js))
        window.js_result_semaphore.acquire()

        return window.js_result
