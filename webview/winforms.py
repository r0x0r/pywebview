# -*- coding: utf-8 -*-

"""
(C) 2014-2016 Roman Sirokov and contributors
Licensed under BSD license

http://github.com/r0x0r/pywebview/
"""

import os
import sys
import logging
from ctypes import windll

import clr
clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Threading")
import System.Windows.Forms as WinForms
from System import IntPtr, Int32
from System.Threading import Thread, ThreadStart, ApartmentState
from System.Drawing import Size, Point, Icon

from webview import OPEN_DIALOG, FOLDER_DIALOG, SAVE_DIALOG
from webview.localization import localization
from webview.win32_shared import set_ie_mode


logger = logging.getLogger(__name__)


class BrowserView:
    class BrowserForm(WinForms.Form):
        def __init__(self, title, url, width, height, resizable, fullscreen, min_size, confirm_quit, webview_ready):
            self.Text = title
            self.ClientSize = Size(width, height)
            self.MinimumSize = Size(min_size[0], min_size[1])

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
            self.web_browser.ScriptErrorsSuppressed = True
            self.web_browser.IsWebBrowserContextMenuEnabled = False

            self.cancel_back = False
            self.web_browser.PreviewKeyDown += self.on_preview_keydown
            self.web_browser.Navigating += self.on_navigating

            if url:
                self.web_browser.Navigate(url)

            self.Controls.Add(self.web_browser)
            self.is_fullscreen = False
            self.Shown += self.on_shown

            if confirm_quit:
                self.FormClosing += self.on_closing

            if fullscreen:
                self.toggle_fullscreen()

        def on_shown(self, sender, args):
            self.webview_ready.set()

        def on_closing(self, sender, args):
            result = WinForms.MessageBox.Show(localization["global.quitConfirmation"], self.Text,
                                              WinForms.MessageBoxButtons.OKCancel, WinForms.MessageBoxIcon.Asterisk)

            if result == WinForms.DialogResult.Cancel:
                args.Cancel = True

        def on_preview_keydown(self, sender, args):
            if args.KeyCode == WinForms.Keys.Back:
                self.cancel_back = True

        def on_navigating(self, sender, args):
            if self.cancel_back:
                args.Cancel = True
                self.cancel_back = False

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

                windll.user32.SetWindowPos(self.Handle.ToInt32(), None, screen.Bounds.X, screen.Bounds.Y, screen.Bounds.Width, screen.Bounds.Height, 64)
            else:
                self.TopMost = False
                self.Size = self.old_size
                self.WindowState = self.old_state
                self.FormBorderStyle = self.old_style
                self.Location = self.old_location
                self.is_fullscreen = False

    instance = None

    def __init__(self, title, url, width, height, resizable, fullscreen, min_size, confirm_quit, webview_ready):
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
        self.browser = None

    def show(self):
        def start():
            app = WinForms.Application
            self.browser = BrowserView.BrowserForm(self.title, self.url, self.width,self.height, self.resizable,
                                                   self.fullscreen, self.min_size, self.confirm_quit, self.webview_ready)
            app.Run(self.browser)

        thread = Thread(ThreadStart(start))
        thread.SetApartmentState(ApartmentState.STA)
        thread.Start()
        thread.Join()

    def destroy(self):
        self.browser.Close()

    def get_current_url(self):
        return self.browser.web_browser.Url.AbsoluteUri

    def load_url(self, url):
        self.url = url
        self.browser.web_browser.Navigate(url)

    def load_html(self, content):
        self.browser.web_browser.DocumentText = content

    def create_file_dialog(self, dialog_type, directory, allow_multiple, save_filename):
        if not directory:
            directory = os.environ["HOMEPATH"]

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
                dialog.Filter = localization["windows.fileFilter.allFiles"] + " (*.*)|*.*"
                dialog.RestoreDirectory = True

                result = dialog.ShowDialog(BrowserView.instance.browser)
                if result == WinForms.DialogResult.OK:
                    file_path = tuple(dialog.FileNames)
                else:
                    file_path = None

            elif dialog_type == SAVE_DIALOG:
                dialog = WinForms.SaveFileDialog()
                dialog.Filter = localization["windows.fileFilter.allFiles"] + " (*.*)|"
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
            logger.exception("Error invoking {0} dialog".format(dialog_type))
            return None

    def toggle_fullscreen(self):
        self.browser.toggle_fullscreen()


def create_window(title, url, width, height, resizable, fullscreen, min_size, confirm_quit, webview_ready):
    set_ie_mode()
    browser_view = BrowserView(title, url, width, height, resizable, fullscreen, min_size, confirm_quit, webview_ready)
    browser_view.show()


def create_file_dialog(dialog_type, directory, allow_multiple, save_filename):
    return BrowserView.instance.create_file_dialog(dialog_type, directory, allow_multiple, save_filename)


def get_current_url():
    return BrowserView.instance.get_current_url()


def load_url(url):
    BrowserView.instance.load_url(url)


def load_html(content, base_uri):
    BrowserView.instance.load_html(content)


def toggle_fullscreen():
    BrowserView.instance.toggle_fullscreen()


def destroy_window():
    BrowserView.instance.destroy()
