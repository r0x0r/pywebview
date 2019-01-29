# -*- coding: utf-8 -*-

"""
(C) 2014-2018 Roman Sirokov and contributors
Licensed under BSD license

http://github.com/r0x0r/pywebview/
"""

import os
import sys
import logging
import json
import webbrowser
from ctypes import windll
from threading import Event

from webview import OPEN_DIALOG, FOLDER_DIALOG, SAVE_DIALOG, _js_bridge_call
from webview.util import webview_toolkit_ui_dll_path, parse_file_type, inject_base_uri, default_html, parse_api_js
from webview.js.css import disable_text_select
from webview.localization import localization

import clr

clr.AddReference('System.Collections')
clr.AddReference('System.Windows.Forms')
clr.AddReference(webview_toolkit_ui_dll_path())

# noinspection PyUnresolvedReferences
import System.Windows.Forms as WinForms
# noinspection PyUnresolvedReferences
from System import IntPtr, Int32, Func, Type, Environment, Action
# noinspection PyUnresolvedReferences
from System.Drawing import Size, Point, Icon, Color, ColorTranslator, SizeF
# noinspection PyUnresolvedReferences
from System.Collections.Generic import List
# noinspection PyUnresolvedReferences
from System.Threading import Thread, ThreadStart, ApartmentState
# noinspection PyUnresolvedReferences
from System.ComponentModel import ISupportInitialize
# noinspection PyUnresolvedReferences
from Microsoft.Toolkit.Forms.UI.Controls import WebView


logger = logging.getLogger('pywebview')


class BrowserView:
    instances = {}

    class BrowserForm(WinForms.Form):
        def __init__(self, uid, title, url, width, height, resizable, fullscreen, min_size,
                     confirm_quit, background_color, debug, js_api, text_select, webview_ready):
            # Class properties
            self.uid = uid
            self.url = url
            self.js_api = js_api
            self.load_event = Event()
            self.text_select = text_select
            self.is_fullscreen = False
            self.webview_ready = webview_ready

            # Form properties
            self.Text = title
            self.BackColor = ColorTranslator.FromHtml(background_color)
            self.ClientSize = Size(width, height)
            self.MinimumSize = Size(min_size[0], min_size[1])
            self.AutoScaleMode = WinForms.AutoScaleMode.Dpi
            self.AutoScaleDimensions = SizeF(96.0, 96.0)
            if not resizable:
                self.MaximizeBox = False
                self.FormBorderStyle = WinForms.FormBorderStyle.FixedSingle

            # Application icon
            handle = windll.kernel32.GetModuleHandleW(None)
            icon_handle = windll.shell32.ExtractIconW(handle, sys.executable, 0)
            if icon_handle != 0:
                self.Icon = Icon.FromHandle(IntPtr.op_Explicit(Int32(icon_handle))).Clone()
            windll.user32.DestroyIcon(icon_handle)

            # Initialize WebView and add it to the Window's controls
            # https://gist.github.com/kypflug/14e0738c80940bbb80babd626de7eef4
            self.web_view = WebView()
            life = ISupportInitialize(self.web_view)
            life.BeginInit()
            self.Controls.Add(self.web_view)

            # WebView Properties
            self.web_view.Dock = WinForms.DockStyle.Fill
            self.web_view.DpiAware = True  # Don't know if this is needed
            self.web_view.IsIndexedDBEnabled = True
            self.web_view.IsJavaScriptEnabled = True
            self.web_view.IsScriptNotifyAllowed = True
            self.web_view.DefaultBackgroundColor = self.BackColor

            # WebView Events
            self.web_view.ScriptNotify += self.on_script_notify
            self.web_view.NewWindowRequested += self.on_new_window_request
            self.web_view.NavigationStarting += self.on_navigation_started
            self.web_view.NavigationCompleted += self.on_navigation_completed
            self.web_view.UnviewableContentIdentified += self.on_unviewable_content_identified

            # End initialization
            life.EndInit()

            # Form Events
            self.Shown += self.on_shown
            self.FormClosed += self.on_close
            if confirm_quit:
                self.FormClosing += self.on_closing

            # Load web page
            if url:
                # Load URL
                self.web_view.Navigate(url)
            else:
                # No URL load blank HTML
                self.web_view.NavigateToString(default_html)

            # Set fullscreen if needed
            if fullscreen:
                self.toggle_fullscreen()

        def on_shown(self, _, __):
            self.webview_ready.set()

        def on_close(self, _, __):
            del BrowserView.instances[self.uid]

            if len(BrowserView.instances) == 0:
                WinForms.Application.Exit()

        def on_closing(self, _, args):
            result = WinForms.MessageBox.Show(localization['global.quitConfirmation'], self.Text,
                                              WinForms.MessageBoxButtons.OKCancel, WinForms.MessageBoxIcon.Asterisk)

            if result == WinForms.DialogResult.Cancel:
                args.Cancel = True

        def on_script_notify(self, _, args):
            func_name, func_param = json.loads(args.get_Value())
            print(func_name)

            if func_name == 'alert':
                WinForms.MessageBox.Show(func_param)
            else:
                _js_bridge_call(self.uid, self.js_api, func_name, func_param)

        def on_new_window_request(self, _, args):
            webbrowser.open(str(args.get_Uri()))
            args.set_Handled(True)

        def on_navigation_started(self, sender, args):
            # FIXME: This alert shim is non-blocking
            self.web_view.AddInitializeScript("window.alert = (msg) => window.external.notify(JSON.stringify(['alert', msg+'']))")

            if self.js_api:
                self.web_view.AddInitializeScript(parse_api_js(self.js_api, web_platform="Win_Form_WebView"))

            if not self.text_select:
                self.web_view.AddInitializeScript(disable_text_select)

        def on_navigation_completed(self, sender, args):
            self.load_event.set()

        def on_unviewable_content_identified(self, sender, args):
            # TODO: Use this to implement download
            print(args.get_MediaType(), args.get_Uri())

        def toggle_fullscreen(self):
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

        def set_window_size(self, width, height):
            windll.user32.SetWindowPos(self.Handle.ToInt32(), None, self.Location.X, self.Location.Y,
                                       width, height, 64)


def create_window(uid, title, url, width, height, resizable, fullscreen, min_size,
                  confirm_quit, background_color, debug, js_api, text_select, webview_ready):
    def create():
        window = BrowserView.BrowserForm(uid, title, url, width, height, resizable, fullscreen,
                                         min_size, confirm_quit, background_color, debug, js_api,
                                         text_select, webview_ready)
        BrowserView.instances[uid] = window
        window.Show()

        if uid == 'master':
            app.Run()

    webview_ready.clear()
    app = WinForms.Application

    if uid == 'master':
        if sys.getwindowsversion().major >= 6:
            windll.user32.SetProcessDPIAware()

        app.EnableVisualStyles()
        app.SetCompatibleTextRenderingDefault(False)

        thread = Thread(ThreadStart(create))
        thread.SetApartmentState(ApartmentState.STA)
        thread.Start()
        thread.Join()
    else:
        i = list(BrowserView.instances.values())[0]  # arbitrary instance
        i.Invoke(Func[Type](create))


def set_title(title, uid):
    BrowserView.instances[uid].Text = title

def create_file_dialog(dialog_type, directory, allow_multiple, save_filename, file_types):
    window = list(BrowserView.instances.values())[0]  # arbitrary instance

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
        else:
            raise RuntimeError("Invalid dialog type")

        return file_path
    except:
        logger.exception('Error invoking {0} dialog'.format(dialog_type))
        return None


def get_current_url(uid):
    window = BrowserView.instances[uid]

    if window.url is None:
        return None
    else:
        window.load_event.wait()
        return window.web_view.Source.AbsoluteUri


def load_url(url, uid):
    window = BrowserView.instances[uid]
    window.load_event.clear()
    window.url = url
    window.web_view.Navigate(url)


def load_html(content, base_uri, uid):
    window = BrowserView.instances[uid]
    window.load_event.clear()
    window.web_view.NavigateToString(inject_base_uri(content, base_uri))


def toggle_fullscreen(uid):
    window = BrowserView.instances[uid]
    window.toggle_fullscreen()


def set_window_size(width, height, uid):
    window = BrowserView.instances[uid]
    window.set_window_size(width, height)


def destroy_window(uid):
    window = BrowserView.instances[uid]
    window.Close()


def evaluate_js(script, uid):
    window = BrowserView.instances[uid]
    window.load_event.wait()
    result = window.web_browser.InvokeScript('eval', (script,))
    return None if result is None or result is 'null' else json.loads(result)
