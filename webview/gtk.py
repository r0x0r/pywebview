"""
(C) 2014-2015 Roman Sirokov
Licensed under BSD license

http://github.com/r0x0r/pywebview/
"""

import logging
from webview import OPEN_DIALOG, FOLDER_DIALOG, SAVE_DIALOG

logger = logging.getLogger(__name__)


try:
    # Try GTK 3
    from gi.repository import Gtk as gtk
    from gi.repository import Gdk
    from gi.repository import WebKit as webkit
except ImportError as e:
    import_error = True
    logger.warn("PyGObject is not found", exc_info=True)
else:
    import_error = False


class BrowserView:
    instance = None

    def __init__(self, title, url, width, height, resizable, fullscreen):
        BrowserView.instance = self

        Gdk.threads_init()
        window = gtk.Window(title=title)

        window.set_size_request(width, height)
        window.set_resizable(resizable)
        window.set_position(gtk.WindowPosition.CENTER)

        if fullscreen:
            window.fullscreen()

        window.connect("delete-event", gtk.main_quit)

        scrolled_window = gtk.ScrolledWindow()
        window.add(scrolled_window)

        webview = webkit.WebView()
        webview.props.settings.props.enable_default_context_menu = False
        scrolled_window.add_with_viewport(webview)
        window.show_all()
        webview.load_uri(url)

        self.window = window
        self.webview = webview

    def show(self):
        Gdk.threads_enter()
        gtk.main()
        Gdk.threads_leave()

    def create_file_dialog(self, dialog_type, allow_multiple):
        Gdk.threads_enter()

        if dialog_type == FOLDER_DIALOG:
            gtk_dialog_type = gtk.FileChooserAction.SELECT_FOLDER
        else:
            gtk_dialog_type = gtk.FileChooserAction.OPEN

        dialog = gtk.FileChooserDialog("Please choose a file", self.window, gtk_dialog_type,
                                       (gtk.STOCK_CANCEL, gtk.ResponseType.CANCEL, gtk.STOCK_OPEN, gtk.ResponseType.OK))

        dialog.set_select_multiple(allow_multiple)

        response = dialog.run()

        if response == gtk.ResponseType.OK:
            if not allow_multiple or len(dialog.get_filenames()) == 1:
                file_name = dialog.get_filename()
            else:
                file_name = dialog.get_filenames()
        else:
            file_name = None

        dialog.destroy()

        Gdk.threads_leave()

        return file_name

    def load_url(self, url):
        self.webview.load_uri(url)


def create_window(title, url, width, height, resizable, fullscreen):
    browser = BrowserView(title, url, width, height, resizable, fullscreen)
    browser.show()


def load_url(url):
    if BrowserView.instance is not None:
        BrowserView.instance.load_url(url)
    else:
        raise Exception("Create a web view window first, before invoking this function")


def create_file_dialog(dialog_type, allow_multiple):
    if BrowserView.instance is not None:
        return BrowserView.instance.create_file_dialog(dialog_type, allow_multiple)
    else:
        raise Exception("Create a web view window first, before invoking this function")
