'''
(C) 2014-2019 Roman Sirokov and contributors
Licensed under BSD license

http://github.com/r0x0r/pywebview/
'''

import os
import platform
import json
import logging
import webbrowser
import socket
from uuid import uuid1
from copy import deepcopy
from threading import Semaphore, Event

from webview import _debug, _user_agent, OPEN_DIALOG, FOLDER_DIALOG, SAVE_DIALOG, windows
from webview.window import Window, FixPoint
from webview.util import convert_string, default_html, parse_api_js, js_bridge_call
from webview.js.css import disable_text_select
from webview.screen import Screen
from webview.window import FixPoint


logger = logging.getLogger('pywebview')

settings = {}

from qtpy import QtCore

logger.debug('Using Qt %s' % QtCore.__version__)

from qtpy.QtWidgets import QMainWindow, QApplication, QFileDialog, QMessageBox, QAction
from qtpy.QtGui import QColor, QScreen

try:
    from qtpy.QtWebEngineWidgets import QWebEngineView as QWebView, QWebEnginePage as QWebPage
    from qtpy.QtWebChannel import QWebChannel
    renderer = 'qtwebengine'
    is_webengine = True
except ImportError:
    from PyQt5 import QtWebKitWidgets
    from PyQt5.QtWebKitWidgets import QWebView, QWebPage
    is_webengine = False
    renderer = 'qtwebkit'

_main_window_created = Event()
_main_window_created.clear()

# suppress invalid style override error message on some Linux distros
os.environ['QT_STYLE_OVERRIDE'] = ''


class BrowserView(QMainWindow):
    instances = {}
    inspector_port = None  # The localhost port at which the Remote debugger listens

    create_window_trigger = QtCore.Signal(object)
    set_title_trigger = QtCore.Signal(str)
    load_url_trigger = QtCore.Signal(str)
    html_trigger = QtCore.Signal(str, str)
    dialog_trigger = QtCore.Signal(int, str, bool, str, str)
    destroy_trigger = QtCore.Signal()
    hide_trigger = QtCore.Signal()
    show_trigger = QtCore.Signal()
    fullscreen_trigger = QtCore.Signal()
    window_size_trigger = QtCore.Signal(int, int, FixPoint)
    window_move_trigger = QtCore.Signal(int, int)
    window_minimize_trigger = QtCore.Signal()
    window_restore_trigger = QtCore.Signal()
    current_url_trigger = QtCore.Signal()
    evaluate_js_trigger = QtCore.Signal(str, str)
    on_top_trigger = QtCore.Signal(bool)

    class JSBridge(QtCore.QObject):
        qtype = QtCore.QJsonValue if is_webengine else str

        def __init__(self):
            super(BrowserView.JSBridge, self).__init__()

        @QtCore.Slot(str, qtype, str, result=str)
        def call(self, func_name, param, value_id):
            func_name = BrowserView._convert_string(func_name)
            param = BrowserView._convert_string(param)

            return js_bridge_call(self.window, func_name, json.loads(param), value_id)

    class WebView(QWebView):
        def __init__(self, parent=None):
            super(BrowserView.WebView, self).__init__(parent)

            if parent.frameless and parent.easy_drag:
                QApplication.instance().installEventFilter(self)
                self.setMouseTracking(True)

            self.transparent = parent.transparent
            if parent.transparent:
                self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
                self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent, False)
                self.setStyleSheet("background: transparent;")

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
                inspect_element = QAction('Inspect Element', menu)
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
                print(url)
                window = Window('web_inspector', title, url, '', 700, 500, None, None, True, False,
                                (300, 200), False, False, False, False, False, False, '#fff', None, False, False, None)
                window.localization = self.parent().localization

                inspector = BrowserView(window)
                inspector.show()

        def mousePressEvent(self, event):
            if event.button() == QtCore.Qt.LeftButton:
                self.drag_pos = event.globalPos() - self.parent().frameGeometry().topLeft()

            event.accept()

        def mouseMoveEvent(self, event):
            parent = self.parent()
            if parent.frameless and parent.easy_drag and int(event.buttons()) == 1:  # left button is pressed
                parent.move(event.globalPos() - self.drag_pos)

        def eventFilter(self, object, event):
            if object.parent() == self:
                if event.type() == QtCore.QEvent.MouseMove:
                    self.mouseMoveEvent(event)
                elif event.type() == QtCore.QEvent.MouseButtonPress:
                    self.mousePressEvent(event)

            return False

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
            if is_webengine:
                self.featurePermissionRequested.connect(self.onFeaturePermissionRequested)
                self.nav_handler = BrowserView.NavigationHandler(self)
            else:
                self.nav_handler = None

            if parent.transparent:
                self.setBackgroundColor(QtCore.Qt.transparent)

        if is_webengine:
            def onFeaturePermissionRequested(self, url, feature):
                if feature in (
                    QWebPage.MediaAudioCapture,
                    QWebPage.MediaVideoCapture,
                    QWebPage.MediaAudioVideoCapture,
                ):
                    self.setFeaturePermission(url, feature, QWebPage.PermissionGrantedByUser)
                else:
                    self.setFeaturePermission(url, feature, QWebPage.PermissionDeniedByUser)
        else:
            def acceptNavigationRequest(self, frame, request, type):
                if frame is None:
                    webbrowser.open(request.url().toString(), 2, True)
                    return False
                return True

        def userAgentForUrl(self, url):
            user_agent = settings.get('user_agent') or _user_agent
            if user_agent:
                return user_agent
            else:
                return super().userAgentForUrl(url)

        def createWindow(self, type):
            return self.nav_handler

    def __init__(self, window):
        super(BrowserView, self).__init__()
        BrowserView.instances[window.uid] = self
        self.uid = window.uid
        self.pywebview_window = window

        self.js_bridge = BrowserView.JSBridge()
        self.js_bridge.window = window

        self.is_fullscreen = False
        self.confirm_close = window.confirm_close
        self.text_select = window.text_select

        self._file_name_semaphore = Semaphore(0)
        self._current_url_semaphore = Semaphore(0)

        self.loaded = window.events.loaded
        self.shown = window.events.shown

        self.localization = window.localization

        self._js_results = {}
        self._current_url = None
        self._file_name = None

        self.resize(window.initial_width, window.initial_height)
        self.title = window.title
        self.setWindowTitle(window.title)

        # Set window background color
        self.background_color = QColor()
        self.background_color.setNamedColor(window.background_color)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), self.background_color)
        self.setPalette(palette)

        if not window.resizable:
            self.setFixedSize(window.initial_width, window.initial_height)

        self.setMinimumSize(window.min_size[0], window.min_size[1])

        self.frameless = window.frameless
        self.easy_drag = window.easy_drag
        flags = self.windowFlags()
        if self.frameless:
            flags = flags | QtCore.Qt.FramelessWindowHint

        if window.on_top:
            flags = flags | QtCore.Qt.WindowStaysOnTopHint

        self.setWindowFlags(flags)

        self.transparent = window.transparent
        if self.transparent:
            # Override the background color
            self.background_color = QColor('transparent')
            palette = self.palette()
            palette.setColor(self.backgroundRole(), self.background_color)
            self.setPalette(palette)
            # Enable the transparency hint
            self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.view = BrowserView.WebView(self)

        if is_webengine:
            os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = (
                '--use-fake-ui-for-media-stream --enable-features=AutoplayIgnoreWebAudio')

        if _debug['mode'] and is_webengine:
            # Initialise Remote debugging (need to be done only once)
            if not BrowserView.inspector_port:
                BrowserView.inspector_port = BrowserView._get_debug_port()
                os.environ['QTWEBENGINE_REMOTE_DEBUGGING'] = BrowserView.inspector_port
        else:
            self.view.setContextMenuPolicy(QtCore.Qt.NoContextMenu)  # disable right click context menu

        self.view.setPage(BrowserView.WebPage(self.view))
        self.view.page().loadFinished.connect(self.on_load_finished)

        self.setCentralWidget(self.view)

        self.create_window_trigger.connect(BrowserView.on_create_window)
        self.load_url_trigger.connect(self.on_load_url)
        self.html_trigger.connect(self.on_load_html)
        self.dialog_trigger.connect(self.on_file_dialog)
        self.destroy_trigger.connect(self.on_destroy_window)
        self.show_trigger.connect(self.on_show_window)
        self.hide_trigger.connect(self.on_hide_window)
        self.fullscreen_trigger.connect(self.on_fullscreen)
        self.window_size_trigger.connect(self.on_window_size)
        self.window_move_trigger.connect(self.on_window_move)
        self.window_minimize_trigger.connect(self.on_window_minimize)
        self.window_restore_trigger.connect(self.on_window_restore)
        self.current_url_trigger.connect(self.on_current_url)
        self.evaluate_js_trigger.connect(self.on_evaluate_js)
        self.set_title_trigger.connect(self.on_set_title)
        self.on_top_trigger.connect(self.on_set_on_top)

        if is_webengine and platform.system() != 'OpenBSD':
            self.channel = QWebChannel(self.view.page())
            self.view.page().setWebChannel(self.channel)

        if window.fullscreen:
            self.toggle_fullscreen()

        if window.real_url is not None:
            self.view.setUrl(QtCore.QUrl(window.real_url))
        elif window.uid == 'web_inspector':
            self.view.setUrl(QtCore.QUrl(window.original_url))
        elif window.html:
            self.view.setHtml(window.html, QtCore.QUrl(''))
        else:
            self.view.setHtml(default_html, QtCore.QUrl(''))

        if window.initial_x is not None and window.initial_y is not None:
            self.move(window.initial_x, window.initial_y)
        else:
            center = QApplication.desktop().availableGeometry().center() - self.rect().center()
            self.move(center.x(), center.y())

        if not window.minimized:
            self.activateWindow()
            self.raise_()

        self.shown.set()

    def on_set_title(self, title):
        self.setWindowTitle(title)

    def on_file_dialog(self, dialog_type, directory, allow_multiple, save_filename, file_filter):
        if dialog_type == FOLDER_DIALOG:
            self._file_name = QFileDialog.getExistingDirectory(self, self.localization['linux.openFolder'], options=QFileDialog.ShowDirsOnly)
        elif dialog_type == OPEN_DIALOG:
            if allow_multiple:
                self._file_name = QFileDialog.getOpenFileNames(self, self.localization['linux.openFiles'], directory, file_filter)
            else:
                self._file_name = QFileDialog.getOpenFileName(self, self.localization['linux.openFile'], directory, file_filter)
        elif dialog_type == SAVE_DIALOG:
            if directory:
                save_filename = os.path.join(str(directory), str(save_filename))

            self._file_name = QFileDialog.getSaveFileName(self, self.localization['global.saveFile'], save_filename)

        self._file_name_semaphore.release()

    def on_current_url(self):
        url = BrowserView._convert_string(self.view.url().toString())
        self._current_url = None if url == '' or url.startswith('data:text/html') else url
        self._current_url_semaphore.release()

    def on_load_url(self, url):
        self.view.setUrl(QtCore.QUrl(url))

    def on_load_html(self, content, base_uri):
        self.view.setHtml(content, QtCore.QUrl(base_uri))

    def on_set_on_top(self, top):
        flags = self.windowFlags()
        if top:
            self.setWindowFlags(flags | QtCore.Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~QtCore.Qt.WindowStaysOnTopHint)

        self.show()

    def closeEvent(self, event):
        if self.confirm_close:
            reply = QMessageBox.question(self, self.title, self.localization['global.quitConfirmation'],
                                         QMessageBox.Yes, QMessageBox.No)

            if reply == QMessageBox.No:
                event.ignore()
                return

        should_cancel = self.pywebview_window.events.closing.set()

        if should_cancel:
            event.ignore()
            return

        event.accept()
        BrowserView.instances[self.uid].close()
        del BrowserView.instances[self.uid]

        if self.pywebview_window in windows:
            windows.remove(self.pywebview_window)

        self.pywebview_window.events.closed.set()

        if len(BrowserView.instances) == 0:
            self.hide()
            _app.exit()

    def changeEvent(self, e):
        if e.type() != QtCore.QEvent.WindowStateChange:
            return

        if self.windowState() == QtCore.Qt.WindowMinimized:
            self.pywebview_window.events.minimized.set()

        if self.windowState() == QtCore.Qt.WindowMaximized:
            self.pywebview_window.events.maximized.set()

        if self.windowState() == QtCore.Qt.WindowNoState and e.oldState() in (QtCore.Qt.WindowMinimized, QtCore.Qt.WindowMaximized):
            self.pywebview_window.events.restored.set()

    def resizeEvent(self, e):
        if self.pywebview_window.initial_width != self.width() or \
           self.pywebview_window.initial_height != self.height():
            self.pywebview_window.events.resized.set(self.width(), self.height())

    def on_show_window(self):
        self.show()

    def on_hide_window(self):
        self.hide()

    def on_destroy_window(self):
        self.close()

    def on_fullscreen(self):
        if self.is_fullscreen:
            self.showNormal()
        else:
            self.showFullScreen()

        self.is_fullscreen = not self.is_fullscreen

    def on_window_size(self, width, height, fix_point):
        geo = self.geometry()

        if fix_point & FixPoint.EAST:
            # Keep the right of the window in the same place
            geo.setX(geo.x() + geo.width() - width)

        if fix_point & FixPoint.SOUTH:
            # Keep the top of the window in the same place
            geo.setY(geo.y() + geo.height() - height)

        self.setGeometry(geo)
        self.setFixedSize(width, height)

    def on_window_move(self, x, y):
        self.move(x, y)

    def on_window_minimize(self):
        self.setWindowState(QtCore.Qt.WindowMinimized)

    def on_window_restore(self):
        self.setWindowState(QtCore.Qt.WindowNoState)
        self.raise_()
        self.activateWindow()

    def on_evaluate_js(self, script, uuid):
        def return_result(result):
            result = BrowserView._convert_string(result)
            uuid_ = BrowserView._convert_string(uuid)

            js_result = self._js_results[uuid_]
            js_result['result'] = None if result is None or result == 'null' else result if result == '' else json.loads(result)
            js_result['semaphore'].release()

        try:    # < Qt5.6
            self.view.page().runJavaScript(script, return_result)
        except TypeError:
            self.view.page().runJavaScript(script)  # PySide2 & PySide6
        except AttributeError:
            result = self.view.page().mainFrame().evaluateJavaScript(script)
            return_result(result)
        except Exception as e:
            logger.exception(e)

    def on_load_finished(self):
        if self.uid == 'web_inspector':
            return

        self._set_js_api()

        if not self.text_select:
            script = disable_text_select.replace('\n', '')

            try:
                self.view.page().runJavaScript(script)
            except: # QT < 5.6
                self.view.page().mainFrame().evaluateJavaScript(script)


    def set_title(self, title):
        self.set_title_trigger.emit(title)

    def get_current_url(self):
        self.loaded.wait()
        self.current_url_trigger.emit()
        self._current_url_semaphore.acquire()

        return self._current_url

    def load_url(self, url):
        self.loaded.clear()
        self.load_url_trigger.emit(url)

    def load_html(self, content, base_uri):
        self.loaded.clear()
        self.html_trigger.emit(content, base_uri)

    def create_file_dialog(self, dialog_type, directory, allow_multiple, save_filename, file_filter):
        self.dialog_trigger.emit(dialog_type, directory, allow_multiple, save_filename, file_filter)
        self._file_name_semaphore.acquire()

        if dialog_type == FOLDER_DIALOG:
            file_names = (self._file_name,)
        elif dialog_type == SAVE_DIALOG or not allow_multiple:
            file_names = (self._file_name[0],)
        else:
            file_names = tuple(self._file_name[0])

        # Check if we got an empty tuple, or a tuple with empty string
        if len(file_names) == 0 or len(file_names[0]) == 0:
            return None
        else:
            return file_names

    def hide_(self):
        self.hide_trigger.emit()

    def show_(self):
        self.show_trigger.emit()

    def destroy_(self):
        self.destroy_trigger.emit()

    def toggle_fullscreen(self):
        self.fullscreen_trigger.emit()

    def resize_(self, width, height, fix_point):
        self.window_size_trigger.emit(width, height, fix_point)

    def move_window(self, x, y):
        self.window_move_trigger.emit(x, y)

    def minimize(self):
        self.window_minimize_trigger.emit()

    def restore(self):
        self.window_restore_trigger.emit()

    def set_on_top(self, top):
        self.on_top_trigger.emit(top)

    def evaluate_js(self, script):
        self.loaded.wait()
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

        code = 'qtwebengine' if is_webengine else 'qtwebkit'
        script = parse_api_js(self.js_bridge.window, code)

        if is_webengine:
            qwebchannel_js = QtCore.QFile('://qtwebchannel/qwebchannel.js')
            if qwebchannel_js.open(QtCore.QFile.ReadOnly):
                source = bytes(qwebchannel_js.readAll()).decode('utf-8')
                self.view.page().runJavaScript(source)
                self.channel.registerObject('external', self.js_bridge)
                qwebchannel_js.close()
        else:
            frame = self.view.page().mainFrame()
            _register_window_object()

        try:
            self.view.page().runJavaScript(script)
        except AttributeError:  # < QT 5.6
            self.view.page().mainFrame().evaluateJavaScript(script)

        self.loaded.set()

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
    def _get_debug_port():
        """
        Check if default debug port 8228 is available,
        increment it by 1 until a port is available.
        :return: port: str
        """
        port_available = False
        port = 8228

        while not port_available:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(('localhost', port))
                port_available = True
            except:
                port_available = False
                logger.warning('Port %s is in use' % port)
                port += 1
            finally:
                sock.close()

        return str(port)

    @staticmethod
    # Receive func from subthread and execute it on the main thread
    def on_create_window(func):
        func()


def create_window(window):
    def _create():
        browser = BrowserView(window)

        _main_window_created.set()

        if window.minimized:
            # showMinimized does not work on start without showNormal first
            # looks like a bug in QT
            browser.showNormal()
            browser.showMinimized()
        elif not window.hidden:
            browser.show()

    if window.uid == 'master':
        global _app
        _app = QApplication.instance() or QApplication([])

        _create()
        _app.exec_()
    else:
        _main_window_created.wait()
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


def hide(uid):
    BrowserView.instances[uid].hide_()


def show(uid):
    BrowserView.instances[uid].show_()


def minimize(uid):
    BrowserView.instances[uid].minimize()


def restore(uid):
    BrowserView.instances[uid].restore()


def toggle_fullscreen(uid):
    BrowserView.instances[uid].toggle_fullscreen()


def set_on_top(uid, top):
    BrowserView.instances[uid].set_on_top(top)


def resize(width, height, uid, fix_point):
    BrowserView.instances[uid].resize_(width, height, fix_point)


def move(x, y, uid):
    BrowserView.instances[uid].move_window(x, y)


def create_file_dialog(dialog_type, directory, allow_multiple, save_filename, file_types, uid):
    # Create a file filter by parsing allowed file types
    file_types = [s.replace(';', ' ') for s in file_types]
    file_filter = ';;'.join(file_types)

    i = BrowserView.instances[uid]
    return i.create_file_dialog(dialog_type, directory, allow_multiple, save_filename, file_filter)


def evaluate_js(script, uid):
    return BrowserView.instances[uid].evaluate_js(script)


def get_position(uid):
    position = BrowserView.instances[uid].pos()
    return position.x(), position.y()


def get_size(uid):
    window = BrowserView.instances[uid]
    return window.width(), window.height()


def get_screens():
    global _app
    _app = QApplication.instance() or QApplication([])

    geometries = [s.geometry() for s in _app.screens()]
    screens = [Screen(g.width(), g.height()) for g in geometries]

    return screens
