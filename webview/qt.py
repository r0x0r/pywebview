'''
(C) 2014-2018 Roman Sirokov and contributors
Licensed under BSD license

http://github.com/r0x0r/pywebview/
'''

import os
import platform
import json
import logging
import webbrowser
from uuid import uuid1
from copy import deepcopy
from threading import Semaphore, Event
from socket import socket

from webview.localization import localization
from webview import escape_string, _js_bridge_call
from webview.util import convert_string, parse_api_js
from webview import OPEN_DIALOG, FOLDER_DIALOG, SAVE_DIALOG
from webview.js.css import disable_text_select


logger = logging.getLogger(__name__)


# Try importing Qt5 modules
try:
    from PyQt5 import QtCore

    # Check to see if we're running Qt > 5.5
    from PyQt5.QtCore import QT_VERSION_STR
    _qt_version = [int(n) for n in QT_VERSION_STR.split('.')]

    if _qt_version >= [5, 5] and platform.system() != 'OpenBSD':
        from PyQt5.QtWebEngineWidgets import QWebEngineView as QWebView, QWebEnginePage as QWebPage
        from PyQt5.QtWebChannel import QWebChannel
    else:
        from PyQt5 import QtWebKitWidgets
        from PyQt5.QtWebKitWidgets import QWebView, QWebPage

    from PyQt5.QtWidgets import QWidget, QMainWindow, QVBoxLayout, QApplication, QFileDialog, QMessageBox, QAction
    from PyQt5.QtGui import QColor

    logger.debug('Using Qt5')
except ImportError as e:
    logger.debug('PyQt5 or one of dependencies is not found', exc_info=True)
    _import_error = True
else:
    _import_error = False

if _import_error:
    # Try importing Qt4 modules
    try:
        from PyQt4 import QtCore
        from PyQt4.QtWebKit import QWebView, QWebPage, QWebFrame
        from PyQt4.QtGui import QWidget, QMainWindow, QVBoxLayout, QApplication, QDialog, QFileDialog, QMessageBox, QColor

        _qt_version = [4, 0]
        logger.debug('Using Qt4')
    except ImportError as e:
        _import_error = True
    else:
        _import_error = False

if _import_error:
    raise Exception('This module requires PyQt4 or PyQt5 to work under Linux or *BSD.')


class BrowserView(QMainWindow):
    instances = {}
    inspector_port = None  # The localhost port at which the Remote debugger listens

    create_window_trigger = QtCore.pyqtSignal(object)
    set_title_trigger = QtCore.pyqtSignal(str)
    load_url_trigger = QtCore.pyqtSignal(str)
    html_trigger = QtCore.pyqtSignal(str, str)
    dialog_trigger = QtCore.pyqtSignal(int, str, bool, str, str)
    destroy_trigger = QtCore.pyqtSignal()
    fullscreen_trigger = QtCore.pyqtSignal()
    current_url_trigger = QtCore.pyqtSignal()
    evaluate_js_trigger = QtCore.pyqtSignal(str, str)

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

    class WebView(QWebView):
        def __init__(self, parent=None):
            super(BrowserView.WebView, self).__init__(parent)

        def contextMenuEvent(self, event):
            menu = self.page().createStandardContextMenu()

            # If 'Inspect Element' is present in the default context menu, it
            # means the inspector is already up and running.
            for i in menu.actions():
                if i.text() == 'Inspect Element':
                    break
            else:
                # Inspector is not up yet, so create a pseudo 'Inspect Element'
                # menu that will fire it up.
                inspect_element = QAction('Inspect Element')
                inspect_element.triggered.connect(self.show_inspector)
                menu.addAction(inspect_element)

            menu.exec_(event.globalPos())

        # Create a new webview window pointing at the Remote debugger server
        def show_inspector(self):
            uid = self.parent().uid + '-inspector'
            try:
                # If inspector already exists, bring it to the front
                BrowserView.instances[uid].raise_()
                BrowserView.instances[uid].activateWindow()
            except KeyError:
                title = 'Web Inspector - {}'.format(self.parent().title)
                url = 'http://localhost:{}'.format(BrowserView.inspector_port)

                inspector = BrowserView(uid, title, url, 700, 500, True, False, (300,200),
                                        False, '#fff', False, None, self.parent().webview_ready)
                inspector.show()

    # New-window-requests handler for Qt 5.5+ only
    class NavigationHandler(QWebPage):
        def __init__(self, parent=None):
            super(BrowserView.NavigationHandler, self).__init__(parent)

        def acceptNavigationRequest(self, url, type, is_main_frame):
            webbrowser.open(url.toString(), 2, True)
            return False

    class WebPage(QWebPage):
        def __init__(self, parent=None):
            super(BrowserView.WebPage, self).__init__(parent)
            self.nav_handler = BrowserView.NavigationHandler(self) if _qt_version >= [5, 5] else None

        if _qt_version < [5, 5]:
            def acceptNavigationRequest(self, frame, request, type):
                if frame is None:
                    webbrowser.open(request.url().toString(), 2, True)
                    return False
                return True

        def createWindow(self, type):
            return self.nav_handler

    def __init__(self, uid, title, url, width, height, resizable, fullscreen,
                 min_size, confirm_quit, background_color, debug, js_api, text_select, webview_ready):
        super(BrowserView, self).__init__()
        BrowserView.instances[uid] = self
        self.uid = uid

        self.js_bridge = BrowserView.JSBridge()
        self.js_bridge.api = js_api
        self.js_bridge.parent_uid = self.uid

        self.is_fullscreen = False
        self.confirm_quit = confirm_quit
        self.text_select = text_select

        self._file_name_semaphore = Semaphore(0)
        self._current_url_semaphore = Semaphore(0)

        self.load_event = Event()
        self.webview_ready = webview_ready

        self._js_results = {}
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

        self.view = BrowserView.WebView(self)
        self.view.setPage(BrowserView.WebPage(self.view))

        if debug and _qt_version > [5, 5]:
            # Initialise Remote debugging (need to be done only once)
            if not BrowserView.inspector_port:
                BrowserView.inspector_port = BrowserView._get_free_port()
                os.environ['QTWEBENGINE_REMOTE_DEBUGGING'] = BrowserView.inspector_port
        else:
            self.view.setContextMenuPolicy(QtCore.Qt.NoContextMenu)  # disable right click context menu

        if url is not None:
            self.view.setUrl(QtCore.QUrl(url))
        else:
            self.load_event.set()

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

        if _qt_version >= [5, 5] and platform.system() != 'OpenBSD':
            self.channel = QWebChannel(self.view.page())
            self.view.page().setWebChannel(self.channel)

        self.view.page().loadFinished.connect(self.on_load_finished)

        if fullscreen:
            self.toggle_fullscreen()

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
        url = BrowserView._convert_string(self.view.url().toString())
        self._current_url = None if url == '' else url
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

        try:    # Close inpsector if open
            BrowserView.instances[self.uid + '-inspector'].close()
            del BrowserView.instances[self.uid + '-inspector']
        except KeyError:
            pass

    def on_destroy_window(self):
        self.close()

    def on_fullscreen(self):
        if self.is_fullscreen:
            self.showNormal()
        else:
            self.showFullScreen()

        self.is_fullscreen = not self.is_fullscreen

    def on_evaluate_js(self, script, uuid):
        def return_result(result):
            result = BrowserView._convert_string(result)
            uuid_ = BrowserView._convert_string(uuid)

            js_result = self._js_results[uuid_]
            js_result['result'] = None if result is None or result == 'null' else result if result == '' else json.loads(result)
            js_result['semaphore'].release()


        try:    # PyQt4
            result = self.view.page().mainFrame().evaluateJavaScript(script)
            return_result(result)
        except AttributeError:  # PyQt5
            self.view.page().runJavaScript(script, return_result)

    def on_load_finished(self):
        if self.js_bridge.api:
            self._set_js_api()
        else:
            self.load_event.set()

        if not self.text_select:
            self.evaluate_js(escape_string(disable_text_select))

    def set_title(self, title):
        self.set_title_trigger.emit(title)

    def get_current_url(self):
        self.load_event.wait()
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

        result_semaphore = Semaphore(0)
        unique_id = uuid1().hex
        self._js_results[unique_id] = {'semaphore': result_semaphore, 'result': ''}

        self.evaluate_js_trigger.emit(script, unique_id)
        result_semaphore.acquire()

        result = deepcopy(self._js_results[unique_id]['result'])
        del self._js_results[unique_id]

        return result

    def _set_js_api(self):
        def _register_window_object():
            frame.addToJavaScriptWindowObject('external', self.js_bridge)

        script = parse_api_js(self.js_bridge.api)

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
    def _convert_string(result):
        try:
            if result is None or result.isNull():
                return None

            result = result.toString() # QJsonValue conversion
        except AttributeError:
            pass

        return convert_string(result)

    @staticmethod
    # A simple function to obtain an unused localhost port from the os return it
    def _get_free_port():
        s = socket()
        s.bind(('localhost', 0))
        port = str(s.getsockname()[1])
        s.close()
        return port

    @staticmethod
    # Receive func from subthread and execute it on the main thread
    def on_create_window(func):
        func()


def create_window(uid, title, url, width, height, resizable, fullscreen, min_size,
                  confirm_quit, background_color, debug, js_api, text_select, webview_ready):
    app = QApplication.instance() or QApplication([])

    def _create():
        browser = BrowserView(uid, title, url, width, height, resizable, fullscreen,
                              min_size, confirm_quit, background_color, debug, js_api,
                              text_select, webview_ready)
        browser.show()

    if uid == 'master':
        _create()
        app.exec_()
    else:
        i = list(BrowserView.instances.values())[0] # arbitrary instance
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
