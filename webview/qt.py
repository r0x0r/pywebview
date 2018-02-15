'''
(C) 2014-2016 Roman Sirokov and contributors
Licensed under BSD license

http://github.com/r0x0r/pywebview/
'''

import sys
import os
import re
import logging
from threading import Semaphore, Event

from webview.localization import localization
from webview import _parse_api_js, _js_bridge_call
from webview import OPEN_DIALOG, FOLDER_DIALOG, SAVE_DIALOG


logger = logging.getLogger(__name__)


# Try importing Qt5 modules
try:
    from PyQt5 import QtCore

    # Check to see if we're running Qt > 5.5
    from QtCore import QT_VERSION_STR
    _qt_version = [int(n) for n in QT_VERSION_STR.split('.')]

    if _qt_version >= [5, 5]:
        from PyQt5.QtWebEngineWidgets import QWebEngineView as QWebView
        from PyQt5.QtWebChannel import QWebChannel
    else:
        from PyQt5.QtWebKitWidgets import QWebView

    from PyQt5.QtWidgets import QWidget, QMainWindow, QVBoxLayout, QApplication, QFileDialog, QMessageBox
    from PyQt5.QtGui import QColor

    logger.debug('Using Qt5')
except ImportError as e:
    logger.exception('PyQt5 or one of dependencies is not found')
    _import_error = True
else:
    _import_error = False

if _import_error:
    # Try importing Qt4 modules
    try:
        from PyQt4 import QtCore
        from PyQt4.QtWebKit import QWebView, QWebFrame
        from PyQt4.QtGui import QWidget, QMainWindow, QVBoxLayout, QApplication, QDialog, QFileDialog, QMessageBox, QColor

        _qt_version = [4, 0]
        logger.debug('Using Qt4')
    except ImportError as e:
        logger.exception('PyQt4 or one of dependencies is not found')
        _import_error = True
    else:
        _import_error = False

if _import_error:
    raise Exception('This module requires PyQt4 or PyQt5 to work under Linux.')


class BrowserView(QMainWindow):
    instances = {}

    create_window_trigger = QtCore.pyqtSignal(object)
    set_title_trigger = QtCore.pyqtSignal(str)
    load_url_trigger = QtCore.pyqtSignal(str)
    html_trigger = QtCore.pyqtSignal(str, str)
    dialog_trigger = QtCore.pyqtSignal(int, str, bool, str, str)
    destroy_trigger = QtCore.pyqtSignal()
    fullscreen_trigger = QtCore.pyqtSignal()
    current_url_trigger = QtCore.pyqtSignal()
    evaluate_js_trigger = QtCore.pyqtSignal(str)

    class JSBridge(QtCore.QObject):
        api = None
        parent_uid = None

        try:
            qtype = QtCore.QJsonValue  # QT5
        except AttributeError:
            qtype = str  # QT4

        def __init__(self):
            super(BrowserView.JSBridge, self).__init__()

        @QtCore.pyqtSlot(str, qtype, result=str)
        def call(self, func_name, param):
            func_name = BrowserView._convert_string(func_name)
            param = BrowserView._convert_string(param)

            return _js_bridge_call(self.parent_uid, self.api, func_name, param)

    def __init__(self, uid, title, url, width, height, resizable, fullscreen,
                 min_size, confirm_quit, background_color, debug, js_api, webview_ready):
        super(BrowserView, self).__init__()
        BrowserView.instances[uid] = self
        self.uid = uid

        self.is_fullscreen = False
        self.confirm_quit = confirm_quit

        self._file_name_semaphore = Semaphore(0)
        self._current_url_semaphore = Semaphore()
        self._evaluate_js_semaphore = Semaphore(0)
        self.load_event = Event()

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
        self.set_title_trigger.connect(self.on_set_title)

        self.js_bridge = BrowserView.JSBridge()
        self.js_bridge.api = js_api
        self.js_bridge.parent_uid = self.uid

        if _qt_version >= [5, 5]:
            self.channel = QWebChannel(self.view.page())
            self.view.page().setWebChannel(self.channel)

        self.view.page().loadFinished.connect(self.on_load_finished)

        if fullscreen:
            self.toggle_fullscreen()

        self.view.setContextMenuPolicy(QtCore.Qt.NoContextMenu)  # disable right click context menu

        self.move(QApplication.desktop().availableGeometry().center() - self.rect().center())
        self.activateWindow()
        self.raise_()
        webview_ready.set()

    def on_set_title(self, title):
        self.setWindowTitle(title)

    def on_file_dialog(self, dialog_type, directory, allow_multiple, save_filename, file_filter):
        if dialog_type == FOLDER_DIALOG:
            self._file_name = QFileDialog.getExistingDirectory(self, localization['linux.openFolder'], options=QFileDialog.ShowDirsOnly)
        elif dialog_type == OPEN_DIALOG:
            if allow_multiple:
                self._file_name = QFileDialog.getOpenFileNames(self, localization['linux.openFiles'], directory, file_filter)
            else:
                self._file_name = QFileDialog.getOpenFileName(self, localization['linux.openFile'], directory, file_filter)
        elif dialog_type == SAVE_DIALOG:
            if directory:
                save_filename = os.path.join(str(directory), str(save_filename))

            self._file_name = QFileDialog.getSaveFileName(self, localization['global.saveFile'], save_filename)

        self._file_name_semaphore.release()

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
        del BrowserView.instances[self.uid]

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
            self._evaluate_js_semaphore.release()

        try:    # PyQt4
            return_result(self.view.page().mainFrame().evaluateJavaScript(script))
        except AttributeError:  # PyQt5
            self.view.page().runJavaScript(script, return_result)

    def on_load_finished(self):
        if self.js_bridge.api:
            self._set_js_api()
        else:
            self.load_event.set()

    def set_title(self, title):
        self.set_title_trigger.emit(title)

    def get_current_url(self):
        self.current_url_trigger.emit()
        self._current_url_semaphore.acquire()

        return self._current_url

    def load_url(self, url):
        self.load_event.clear()
        self.load_url_trigger.emit(url)

    def load_html(self, content, base_uri):
        self.load_event.clear()
        self.html_trigger.emit(content, base_uri)

    def create_file_dialog(self, dialog_type, directory, allow_multiple, save_filename, file_filter):
        self.dialog_trigger.emit(dialog_type, directory, allow_multiple, save_filename, file_filter)
        self._file_name_semaphore.acquire()

        if _qt_version >= [5, 0]:  # QT5
            if dialog_type == FOLDER_DIALOG:
                file_names = (self._file_name,)
            elif dialog_type == SAVE_DIALOG or not allow_multiple:
                file_names = (self._file_name[0],)
            else:
                file_names = tuple(self._file_name[0])

        else:  # QT4
            if dialog_type == FOLDER_DIALOG:
                file_names = (BrowserView._convert_string(self._file_name),)
            elif dialog_type == SAVE_DIALOG or not allow_multiple:
                file_names = (BrowserView._convert_string(self._file_name[0]),)
            else:
                file_names = tuple([BrowserView._convert_string(s) for s in self._file_name])

        # Check if we got an empty tuple, or a tuple with empty string
        if len(file_names) == 0 or len(file_names[0]) == 0:
            return None
        else:
            return file_names

    def destroy_(self):
        self.destroy_trigger.emit()

    def toggle_fullscreen(self):
        self.fullscreen_trigger.emit()

    def evaluate_js(self, script):
        self.load_event.wait()

        self.evaluate_js_trigger.emit(script)
        self._evaluate_js_semaphore.acquire()

        return self._evaluate_js_result

    def _set_js_api(self):
        def _register_window_object():
            frame.addToJavaScriptWindowObject('external', self.js_bridge)

        script = _parse_api_js(self.js_bridge.api)

        if _qt_version >= [5, 5]:
            qwebchannel_js = QtCore.QFile('://qtwebchannel/qwebchannel.js')
            if qwebchannel_js.open(QtCore.QFile.ReadOnly):
                source = bytes(qwebchannel_js.readAll()).decode('utf-8')
                self.view.page().runJavaScript(source)
                self.channel.registerObject('external', self.js_bridge)
                qwebchannel_js.close()
        elif _qt_version >= [5, 0]:
            frame = self.view.page().mainFrame()
            _register_window_object()
        else:
            frame = self.view.page().mainFrame()
            _register_window_object()

        try:    # PyQt4
            self.view.page().mainFrame().evaluateJavaScript(script)
        except AttributeError:  # PyQt5
            self.view.page().runJavaScript(script)

        self.load_event.set()


    @staticmethod
    def _convert_string(qstring):
        try:
            qstring = qstring.toString() # QJsonValue conversion
        except:
            pass

        if sys.version < '3':
            return unicode(qstring)
        else:
            return str(qstring)

    @staticmethod
    # Receive func from subthread and execute it on the main thread
    def on_create_window(func):
        func()


def create_window(uid, title, url, width, height, resizable, fullscreen, min_size,
                  confirm_quit, background_color, debug, js_api, webview_ready):
    app = QApplication.instance() or QApplication([])

    def _create():
        browser = BrowserView(uid, title, url, width, height, resizable, fullscreen,
                              min_size, confirm_quit, background_color, debug, js_api,
                              webview_ready)
        browser.show()

    if uid == 'master':
        _create()
        app.exec_()
    else:
        i = list(BrowserView.instances.values())[0]     # arbitary instance
        i.create_window_trigger.emit(_create)


def set_title(title, uid):
    BrowserView.instances[uid].set_title(title)


def get_current_url(uid):
    return BrowserView.instances[uid].get_current_url()


def load_url(url, uid):
    BrowserView.instances[uid].load_url(url)


def load_html(content, base_uri, uid):
    BrowserView.instances[uid].load_html(content, base_uri)


def destroy_window(uid):
    BrowserView.instances[uid].destroy_()


def toggle_fullscreen(uid):
    BrowserView.instances[uid].toggle_fullscreen()


def create_file_dialog(dialog_type, directory, allow_multiple, save_filename, file_types):
    # Create a file filter by parsing allowed file types
    file_types = [s.replace(';', ' ') for s in file_types]
    file_filter = ';;'.join(file_types)

    i = list(BrowserView.instances.values())[0]
    return i.create_file_dialog(dialog_type, directory, allow_multiple, save_filename, file_filter)


def evaluate_js(script, uid):
    return BrowserView.instances[uid].evaluate_js(script)
