import os
import logging

import clr
clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Threading")
import System.Windows.Forms as WinForms
from System.Threading import Thread, ThreadStart, ApartmentState
from System.Drawing import Size, Point

from webview import OPEN_DIALOG, FOLDER_DIALOG, SAVE_DIALOG
from webview.win32 import set_ie_mode
from webview.win32_gen import SetWindowPos, GetSystemMetrics

logger = logging.getLogger(__name__)


class BrowserView:

    class BrowserForm(WinForms.Form):
        def __init__(self, title, url, width, height, resizable, fullscreen, min_size, webview_ready):
            self.Text = title
            self.AutoScaleBaseSize = Size(5, 13)
            self.ClientSize = Size(width, height);
            self.MinimumSize = Size(min_size[0], min_size[1])

            self.webview_ready = webview_ready

            self.web_browser = WinForms.WebBrowser()
            self.web_browser.Dock = WinForms.DockStyle.Fill

            if url:
                self.web_browser.Navigate(url)

            self.Controls.Add(self.web_browser)
            self.is_fullscreen = False
            self.Shown += self.on_shown

            if fullscreen:
                self.toggle_fullscreen()

        def on_shown(self, sender, args):
            self.webview_ready.set()

        def toggle_fullscreen(self):
            if not self.is_fullscreen:
                self.TopMost = True
                self.FormBorderStyle = 0  # FormBorderStyle.None
                self.Bounds = WinForms.Screen.PrimaryScreen.Bounds
                self.WindowState = WinForms.FormWindowState.Maximized
                self.is_fullscreen = True

                screen_x = GetSystemMetrics(0)
                screen_y = GetSystemMetrics(1)
                SetWindowPos(self.Handle.ToInt32(), None, 0, 0, screen_x, screen_y, 64)
            else:
                self.WindowState = WinForms.FormWindowState.Maximized
                self.FormBorderStyle = WinForms.FormBorderStyle.Sizable
                self.is_fullscreen = False

    instance = None

    def __init__(self, title, url, width, height, resizable, fullscreen, min_size, webview_ready):
        BrowserView.instance = self
        self.title = title
        self.url = url
        self.width = width
        self.height = height
        self.resizable = resizable
        self.fullscreen = fullscreen
        self.min_size = min_size
        self.webview_ready = webview_ready
        self.browser = None

    def show(self):
        def start():
            self.browser = BrowserView.BrowserForm(self.title, self.url, self.width,self.height, self.resizable,
                                                   self.fullscreen, self.min_size, self.webview_ready)
            app = WinForms.Application
            app.Run(self.browser)

        thread = Thread(ThreadStart(start))
        thread.SetApartmentState(ApartmentState.STA)
        thread.Start()
        thread.Join()

    def destroy(self):
        self.browser.Close()

    def load_url(self, url):
        self.url = url
        self.browser.web_browser.Navigate(url)

    def load_html(self, content):
        self.browser.web_browser.DocumentText = content

    def create_file_dialog(self, dialog_type, directory, allow_multiple, save_filename):
        if not directory:
            initial_directory = os.environ['HOMEPATH']

        try:
            if dialog_type == FOLDER_DIALOG:
                dialog = WinForms.FolderBrowserDialog()
                dialog.RestoreDirectory = True

                result = dialog.ShowDialog()
                if result == WinForms.DialogResult.OK:
                    file_path = (dialog.SelectedPath,)
                else:
                    file_path = None
            elif dialog_type == OPEN_DIALOG:
                dialog = WinForms.OpenFileDialog();

                dialog.Multiselect = allow_multiple
                dialog.InitialDirectory = initial_directory
                dialog.Filter = "All files (*.*)|*.*"
                dialog.RestoreDirectory = True

                result = dialog.ShowDialog()
                if result == WinForms.DialogResult.OK:
                    file_path = tuple(dialog.FileNames)
                else:
                    file_path = None

            elif dialog_type == SAVE_DIALOG:
                dialog = WinForms.SaveFileDialog()
                dialog.Filter = 'All files (*.*)|'
                dialog.InitialDirectory = initial_directory
                dialog.RestoreDirectory = True
                dialog.FileName = save_filename

                result = dialog.ShowDialog()
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


def create_window(title, url, width, height, resizable, fullscreen, min_size, webview_ready):
    set_ie_mode()
    browser_view = BrowserView(title, url, width, height, resizable, fullscreen, min_size, webview_ready)
    browser_view.show()


def create_file_dialog(dialog_type, directory, allow_multiple, save_filename):
    return BrowserView.instance.create_file_dialog(dialog_type, directory, allow_multiple, save_filename)


def load_url(url):
    BrowserView.instance.load_url(url)


def load_html(content, base_uri):
    BrowserView.instance.load_html(content)


def toggle_fullscreen():
    BrowserView.instance.toggle_fullscreen()


def destroy_window():
    BrowserView.instance.destroy()

