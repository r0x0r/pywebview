"""
(C) 2014-2016 Roman Sirokov and contributors
Licensed under BSD license

http://github.com/r0x0r/pywebview/
"""

import sys
import os
import logging
import threading

from webview.localization import localization
from webview import OPEN_DIALOG, FOLDER_DIALOG, SAVE_DIALOG

logger = logging.getLogger(__name__)


# Try importing Qt4 modules
try:
    from PyQt4 import QtCore
    from PyQt4.QtWebKit import QWebView
    from PyQt4.QtGui import QWidget, QMainWindow, QVBoxLayout, QApplication, QDialog, QFileDialog

    logger.debug("Using Qt4")
except ImportError as e:
    logger.warn("PyQt4 is not found")
    _import_error = True
else:
    _import_error = False


# Try importing Qt5 modules
if _import_error:
    try:
        from PyQt5 import QtCore

        # Check to see if we're running Qt > 5.5
        from PyQt5.QtCore import QT_VERSION_STR
        if float(QT_VERSION_STR[:3]) > 5.5:
            from PyQt5.QtWebEngineWidgets import QWebEngineView as QWebView
        else:
            from PyQt5.QtWebKitWidgets import QWebView

        from PyQt5.QtWidgets import QWidget, QMainWindow, QVBoxLayout, QApplication, QFileDialog

        logger.debug("Using Qt5")
    except ImportError as e:
        logger.exception("PyQt5 is not found")
        _import_error = True
    else:
        _import_error = False


if _import_error:
    raise Exception("This module requires PyQt4 or PyQt5 to work under Linux.")


class BrowserView(QMainWindow):
    instance = None
    load_url_trigger = QtCore.pyqtSignal(str)
    html_trigger = QtCore.pyqtSignal(str, str)
    dialog_trigger = QtCore.pyqtSignal(int, str, bool, str)
    destroy_trigger = QtCore.pyqtSignal()
    fullscreen_trigger = QtCore.pyqtSignal()
    current_url_trigger = QtCore.pyqtSignal()

    def __init__(self, title, url, width, height, resizable, fullscreen, min_size, webview_ready):
        super(BrowserView, self).__init__()
        BrowserView.instance = self
        self.is_fullscreen = False

        self._file_name_semaphor = threading.Semaphore(0)
        self._current_url_semaphore = threading.Semaphore()

        self.resize(width, height)
        self.setWindowTitle(title)

        if not resizable:
            self.setFixedSize(width, height)

        self.setMinimumSize(min_size[0], min_size[1])

        self.view = QWebView(self)
        self.view.setContextMenuPolicy(QtCore.Qt.NoContextMenu)  # disable right click context menu

        if url is not None:
            self.view.setUrl(QtCore.QUrl(url))

        self.setCentralWidget(self.view)
        self.load_url_trigger.connect(self._handle_load_url)
        self.html_trigger.connect(self._handle_load_html)
        self.dialog_trigger.connect(self._handle_file_dialog)
        self.destroy_trigger.connect(self._handle_destroy_window)
        self.fullscreen_trigger.connect(self._handle_fullscreen)
        self.current_url_trigger.connect(self._handle_current_url)

        if fullscreen:
            self.toggle_fullscreen()

        self.move(QApplication.desktop().availableGeometry().center() - self.rect().center())
        self.activateWindow()
        self.raise_()
        webview_ready.set()

    def _handle_file_dialog(self, dialog_type, directory, allow_multiple, save_filename):
        if dialog_type == FOLDER_DIALOG:
            self._file_name = QFileDialog.getExistingDirectory(self, localization["linux.openFolder"], options=QFileDialog.ShowDirsOnly)
        elif dialog_type == OPEN_DIALOG:
            if allow_multiple:
                self._file_name = QFileDialog.getOpenFileNames(self, localization["linux.openFiles"], directory)
            else:
                self._file_name = QFileDialog.getOpenFileName(self, localization["linux.openFile"], directory)
        elif dialog_type == SAVE_DIALOG:
            if directory:
                save_filename = os.path.join(str(directory), str(save_filename))

            self._file_name = QFileDialog.getSaveFileName(self, localization["linux.saveFile"], save_filename)

        self._file_name_semaphor.release()

    def _handle_get_current_url(self):
        self._current_url = self.view.url().toString()
        self._current_url_semaphore.release()

    def _handle_load_url(self, url):
        self.view.setUrl(QtCore.QUrl(url))

    def _handle_load_html(self, content, base_uri):
        self.view.setHtml(content, QtCore.QUrl(base_uri))

    def _handle_destroy_window(self):
        self.close()

    def _handle_fullscreen(self):
        if self.is_fullscreen:
            self.showNormal()
        else:
            self.showFullScreen()

        self.is_fullscreen = not self.is_fullscreen

    def get_current_url(self):
        self.current_url_trigger.emit()
        self._current_url_semaphore.acquire()

        return self._current_url

    def load_url(self, url):
        self.load_url_trigger.emit(url)

    def load_html(self, content, base_uri):
        self.html_trigger.emit(content, base_uri)

    def create_file_dialog(self, dialog_type, directory, allow_multiple, save_filename):
        self.dialog_trigger.emit(dialog_type, directory, allow_multiple, save_filename)
        self._file_name_semaphor.acquire()

        if dialog_type == FOLDER_DIALOG or not allow_multiple:
            return str(self._file_name)
        elif allow_multiple:
            file_names = map(str, self._file_name)

            if len(file_names) == 1:
                return file_names[0]
            else:
                return file_names
        else:
            return None

    def destroy_(self):
        self.destroy_trigger.emit()

    def toggle_fullscreen(self):
        self.fullscreen_trigger.emit()


def create_window(title, url, width, height, resizable, fullscreen, min_size, webview_ready):
    app = QApplication([])

    browser = BrowserView(title, url, width, height, resizable, fullscreen, min_size, webview_ready)
    browser.show()
    app.exec_()


def get_current_url():
    return BrowserView.instance.get_current_url()


def load_url(url):
    BrowserView.instance.load_url(url)


def load_html(content, base_uri):
    BrowserView.instance.load_html(content, base_uri)


def destroy_window():
    BrowserView.instance.destroy_()


def toggle_fullscreen():
    BrowserView.instance.toggle_fullscreen()


def create_file_dialog(dialog_type, directory, allow_multiple, save_filename):
    return BrowserView.instance.create_file_dialog(dialog_type, directory, allow_multiple, save_filename)
