'''
(C) 2014-2016 Roman Sirokov and contributors
Licensed under BSD license

http://github.com/r0x0r/pywebview/
'''

import sys
import os
import re
import logging
import threading

from webview.localization import localization
from webview import OPEN_DIALOG, FOLDER_DIALOG, SAVE_DIALOG
from uuid import uuid4

logger = logging.getLogger(__name__)


# Try importing Qt5 modules
try:
    from PyQt5 import QtCore

    # Check to see if we're running Qt > 5.5
    from PyQt5.QtCore import QT_VERSION_STR
    if float(QT_VERSION_STR[:3]) > 5.5:
        from PyQt5.QtWebEngineWidgets import QWebEngineView as QWebView
    else:
        from PyQt5.QtWebKitWidgets import QWebView

    from PyQt5.QtWidgets import QWidget, QMainWindow, QVBoxLayout, QApplication, QFileDialog, QMessageBox
    from PyQt5.QtGui import QColor

    logger.debug('Using Qt5')
except ImportError as e:
    logger.exception('PyQt5 is not found')
    _import_error = True
else:
    _import_error = False


if _import_error:
    # Try importing Qt4 modules
    try:
        from PyQt4 import QtCore
        from PyQt4.QtWebKit import QWebView
        from PyQt4.QtGui import QWidget, QMainWindow, QVBoxLayout, QApplication, QDialog, QFileDialog, QMessageBox, QColor

        logger.debug('Using Qt4')
    except ImportError as e:
        logger.warn('PyQt4 is not found')
        _import_error = True
    else:
        _import_error = False

if _import_error:
    raise Exception('This module requires PyQt4 or PyQt5 to work under Linux.')


class BrowserView(QMainWindow):
    instances = []

    create_window_trigger = QtCore.pyqtSignal(object)
    load_url_trigger = QtCore.pyqtSignal(str)
    html_trigger = QtCore.pyqtSignal(str, str)
    dialog_trigger = QtCore.pyqtSignal(int, str, bool, str)
    destroy_trigger = QtCore.pyqtSignal()
    fullscreen_trigger = QtCore.pyqtSignal()
    current_url_trigger = QtCore.pyqtSignal()
    evaluate_js_trigger = QtCore.pyqtSignal(str)

    def __init__(self, uid, title, url, width, height, resizable, fullscreen,
                 min_size, confirm_quit, background_color, webview_ready):
        super(BrowserView, self).__init__()
        BrowserView.instances.append(self)
        self.uid = uid

        self.is_fullscreen = False
        self.confirm_quit = confirm_quit

        self._file_name_semaphor = threading.Semaphore(0)
        self._current_url_semaphore = threading.Semaphore()
        self._evaluate_js_semaphor = threading.Semaphore(0)

        self._evaluate_js_result = None
        self._current_url = None
        self._file_name = None

        self.resize(width, height)
        self.title = title
        self.setWindowTitle(title)

        # Set window background color
        self.background_color = QColor()
        self.background_color.setNamedColor(background_color)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), self.background_color)
        self.setPalette(palette)

        if not resizable:
            self.setFixedSize(width, height)

        self.setMinimumSize(min_size[0], min_size[1])

        self.view = QWebView(self)
        self.view.setContextMenuPolicy(QtCore.Qt.NoContextMenu)  # disable right click context menu

        if url is not None:
            self.view.setUrl(QtCore.QUrl(url))

        self.setCentralWidget(self.view)

        self.create_window_trigger.connect(BrowserView.on_create_window)
        self.load_url_trigger.connect(self.on_load_url)
        self.html_trigger.connect(self.on_load_html)
        self.dialog_trigger.connect(self.on_file_dialog)
        self.destroy_trigger.connect(self.on_destroy_window)
        self.fullscreen_trigger.connect(self.on_fullscreen)
        self.current_url_trigger.connect(self.on_current_url)
        self.evaluate_js_trigger.connect(self.on_evaluate_js)

        if fullscreen:
            self.toggle_fullscreen()

        self.move(QApplication.desktop().availableGeometry().center() - self.rect().center())
        self.activateWindow()
        self.raise_()
        webview_ready.set()

    def on_file_dialog(self, dialog_type, directory, allow_multiple, save_filename):
        if dialog_type == FOLDER_DIALOG:
            self._file_name = QFileDialog.getExistingDirectory(self, localization['linux.openFolder'], options=QFileDialog.ShowDirsOnly)
        elif dialog_type == OPEN_DIALOG:
            if allow_multiple:
                self._file_name = QFileDialog.getOpenFileNames(self, localization['linux.openFiles'], directory)
            else:
                self._file_name = QFileDialog.getOpenFileName(self, localization['linux.openFile'], directory)
        elif dialog_type == SAVE_DIALOG:
            if directory:
                save_filename = os.path.join(str(directory), str(save_filename))

            self._file_name = QFileDialog.getSaveFileName(self, localization['global.saveFile'], save_filename)

        self._file_name_semaphor.release()

    def on_current_url(self):
        self._current_url = self.view.url().toString()
        self._current_url_semaphore.release()

    def on_load_url(self, url):
        self.view.setUrl(QtCore.QUrl(url))

    def on_load_html(self, content, base_uri):
        self.view.setHtml(content, QtCore.QUrl(base_uri))

    def closeEvent(self, event):
        if self.confirm_quit:
            reply = QMessageBox.question(self, self.title, localization['global.quitConfirmation'],
                                         QMessageBox.Yes, QMessageBox.No)

            if reply == QMessageBox.No:
                event.ignore()
                return

        event.accept()
        BrowserView.instances.remove(self)

    def on_destroy_window(self):
        self.close()

    def on_fullscreen(self):
        if self.is_fullscreen:
            self.showNormal()
        else:
            self.showFullScreen()

        self.is_fullscreen = not self.is_fullscreen

    def on_evaluate_js(self, script):
        def return_result(result):
            self._evaluate_js_result = result
            self._evaluate_js_semaphor.release()

        try:    # PyQt4
            return_result(self.view.page().mainFrame().evaluateJavaScript(script).toPyObject())
        except AttributeError:  # PyQt5
            self.view.page().runJavaScript(script, return_result)

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

    def evaluate_js(self, script):
        self.evaluate_js_trigger.emit(script)
        self._evaluate_js_semaphor.acquire()

        return self._evaluate_js_result

    @staticmethod
    # Receive func from subthread and execute it on the main thread
    def on_create_window(func):
        func()

    @staticmethod
    def get_instance(attr, value):
        for i in BrowserView.instances:
            try:
                if getattr(i, attr) == value:
                    return i
            except AttributeError:
                break

        return none


def create_window(title, url, width, height, resizable, fullscreen, min_size,
                  confirm_quit, background_color, webview_ready):
    app = QApplication.instance() or QApplication([])

    def _create():
        browser = BrowserView(uid, title, url, width, height, resizable, fullscreen,
                              min_size, confirm_quit, background_color, webview_ready)
        browser.show()

    if not BrowserView.instances:
        uid = 'master'
        _create()
        app.exec_()
    else:
        uid = uuid4().hex
        BrowserView.instances[0].create_window_trigger.emit(_create)

    return uid


def get_current_url(uid='master'):
    try:
        return BrowserView.get_instance('uid', uid).get_current_url()
    except AttributeError:
        pass


def load_url(url, uid='master'):
    try:
        BrowserView.get_instance('uid', uid).load_url(url)
    except AttributeError:
        pass


def load_html(content, base_uri, uid='master'):
    try:
        BrowserView.get_instance('uid', uid).load_html(content, base_uri)
    except AttributeError:
        pass


def destroy_window(uid='master'):
    try:
        BrowserView.get_instance('uid', uid).destroy_()
    except AttributeError:
        pass


def toggle_fullscreen(uid='master'):
    try:
        BrowserView.get_instance('uid', uid).toggle_fullscreen()
    except AttributeError:
        pass


def create_file_dialog(dialog_type, directory, allow_multiple, save_filename):
    return BrowserView.instances[0].create_file_dialog(dialog_type, directory, allow_multiple, save_filename)


def evaluate_js(script, uid='master'):
    try:
        return BrowserView.get_instance('uid', uid).evaluate_js(script)
    except AttributeError:
        pass
