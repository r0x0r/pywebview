import json
import logging
import os
import platform
import socket
import sys
import typing as t
import webbrowser
from copy import copy, deepcopy
from threading import Event, Semaphore, Thread
from uuid import uuid1

from webview import (FOLDER_DIALOG, OPEN_DIALOG, SAVE_DIALOG, _settings, windows)
from webview.js.css import disable_text_select
from webview.menu import Menu, MenuAction, MenuSeparator
from webview.screen import Screen
from webview.util import DEFAULT_HTML, create_cookie, js_bridge_call, parse_api_js, environ_append
from webview.window import FixPoint, Window

logger = logging.getLogger('pywebview')

settings = {}

from qtpy import QtCore

logger.debug('Using Qt %s' % QtCore.__version__)

from qtpy import PYQT6, PYSIDE6
from qtpy.QtGui import QColor, QScreen
from qtpy.QtWidgets import QAction, QApplication, QFileDialog, QMainWindow, QMenuBar, QMessageBox

try:
    from qtpy.QtNetwork import QSslCertificate, QSslConfiguration
    from qtpy.QtWebChannel import QWebChannel
    from qtpy.QtWebEngineWidgets import QWebEnginePage as QWebPage
    from qtpy.QtWebEngineWidgets import QWebEngineProfile
    from qtpy.QtWebEngineWidgets import QWebEngineView as QWebView

    renderer = 'qtwebengine'
    is_webengine = True
except ImportError:
    from PyQt5 import QtWebKitWidgets
    from PyQt5.QtNetwork import QSslCertificate, QSslConfiguration
    from PyQt5.QtWebKitWidgets import QWebPage, QWebView

    is_webengine = False
    renderer = 'qtwebkit'

if is_webengine and QtCore.QSysInfo.productType() in ['arch', 'manjaro', 'nixos']:
    # I don't know why, but it's a common solution for #890 (White screen displayed)
    # such as:
    # - https://github.com/LCA-ActivityBrowser/activity-browser/pull/954/files
    # - https://bugs.archlinux.org/task/73957
    # - https://www.google.com/search?q=arch+rstudio+no+sandbox
    # And sometimes it needs two "--no-sandbox" flags

    environ_append("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox", "--no-sandbox")
    logger.debug("Enable --no-sandbox flag for arch/manjaro/nixos")

_main_window_created = Event()
_main_window_created.clear()

# suppress invalid style override error message on some Linux distros
os.environ['QT_STYLE_OVERRIDE'] = ''
_qt6 = True if PYQT6 or PYSIDE6 else False
_profile_storage_path = _settings['storage_path'] or os.path.join(os.path.expanduser('~'), '.pywebview')


class BrowserView(QMainWindow):
    instances = {}
    inspector_port = None  # The localhost port at which the Remote debugger listens

    # In case we don't have native menubar, we have to save the top level menus and add them
    #     to each window's bar menu
    global_menubar_top_menus = []
    # If we don't save the rest of these, then QApplication can't access them
    global_menubar_other_objects = []
    # The first QMenuBar created
    global_menubar = None

    create_window_trigger = QtCore.Signal(object)
    set_title_trigger = QtCore.Signal(str)
    load_url_trigger = QtCore.Signal(str)
    html_trigger = QtCore.Signal(str, str)
    confirmation_dialog_trigger = QtCore.Signal(str, str, str)
    file_dialog_trigger = QtCore.Signal(int, str, bool, str, str)
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
                self.setStyleSheet('background: transparent;')

        def contextMenuEvent(self, event):
            if _qt6:
                menu = self.createStandardContextMenu()
            else:
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
                window = Window('web_inspector', title, url, '', 700, 500)
                window.localization = self.parent().localization

                inspector = BrowserView(window)
                inspector.show()

        def mousePressEvent(self, event):
            if event.button() == QtCore.Qt.LeftButton:
                self.drag_pos = event.globalPos() - self.parent().frameGeometry().topLeft()

            event.accept()

        def mouseMoveEvent(self, event):
            parent = self.parent()
            if (
                parent.frameless and parent.easy_drag and int(event.buttons()) == 1
            ):  # left button is pressed
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
        def __init__(self, parent=None, profile=None):
            if is_webengine and profile:
                super(BrowserView.WebPage, self).__init__(profile, parent)
            else:
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
            user_agent = settings.get('user_agent') or _settings['user_agent']
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
        self.text_select = window.text_select

        self._file_name_semaphore = Semaphore(0)
        self._current_url_semaphore = Semaphore(0)

        self.loaded = window.events.loaded
        self.shown = window.events.shown

        self.localization = window.localization

        if window.screen:
            if _qt6:
                self.screen = QScreen.availableGeometry(window.screen.frame)
            else:
                self.screen = window.screen.frame.geometry()
        else:
            if _qt6:
                self.screen = QScreen.availableGeometry(QApplication.primaryScreen())
            else:
                self.screen = QApplication.primaryScreen().availableGeometry()

        self._js_results = {}
        self._current_url = None
        self._file_name = None
        self._confirmation_dialog_results = {}

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

        if not window.focus:
            self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating)
            flags = flags | QtCore.Qt.WindowDoesNotAcceptFocus


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
            environ_append(
                'QTWEBENGINE_CHROMIUM_FLAGS',
                '--use-fake-ui-for-media-stream',
                '--enable-features=AutoplayIgnoreWebAudio',
            )

        if _settings['debug'] and is_webengine:
            # Initialise Remote debugging (need to be done only once)
            if not BrowserView.inspector_port:
                BrowserView.inspector_port = BrowserView._get_debug_port()
                os.environ['QTWEBENGINE_REMOTE_DEBUGGING'] = BrowserView.inspector_port
        else:
            self.view.setContextMenuPolicy(
                QtCore.Qt.NoContextMenu
            )  # disable right click context menu

        if is_webengine:
            if _settings['private_mode']:
                self.profile = QWebEngineProfile()
            else:
                self.profile = QWebEngineProfile('pywebview')
                self.profile.setPersistentStoragePath(_profile_storage_path)
                self.cookies = {}
                cookie_store = self.profile.cookieStore()
                cookie_store.cookieAdded.connect(self.on_cookie_added)
                cookie_store.cookieRemoved.connect(self.on_cookie_removed)

                self.view.setPage(BrowserView.WebPage(self.view, profile=self.profile))
        elif not is_webengine and not _settings['private_mode']:
            logger.warning('qtwebkit does not support private_mode')

        self.view.page().loadFinished.connect(self.on_load_finished)
        self.setCentralWidget(self.view)

        self.create_window_trigger.connect(BrowserView.on_create_window)
        self.load_url_trigger.connect(self.on_load_url)
        self.html_trigger.connect(self.on_load_html)
        self.confirmation_dialog_trigger.connect(self.on_confirmation_dialog)
        self.file_dialog_trigger.connect(self.on_file_dialog)
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
            self.view.setHtml(DEFAULT_HTML, QtCore.QUrl(''))

        if window.initial_x is not None and window.initial_y is not None:
            self.move(self.screen.x()+window.initial_x, self.screen.y()+window.initial_y)
        else:
            offset = -16 if _qt6 else 0
            center = self.screen.center() - self.rect().center()
            self.move(center.x(), center.y()+offset)

        if not window.minimized:
            self.activateWindow()
            self.raise_()

        self.shown.set()

    def on_set_title(self, title):
        self.setWindowTitle(title)

    def on_confirmation_dialog(self, title, message, uuid):
        uuid_ = BrowserView._convert_string(uuid)
        reply = QMessageBox.question(self, title, message, QMessageBox.Cancel, QMessageBox.Ok)

        confirmation_dialog_result = self._confirmation_dialog_results[uuid_]

        result = False
        if reply == QMessageBox.Ok:
            result = True
        confirmation_dialog_result['result'] = result
        confirmation_dialog_result['semaphore'].release()

    def on_file_dialog(self, dialog_type, directory, allow_multiple, save_filename, file_filter):
        if dialog_type == FOLDER_DIALOG:
            self._file_name = QFileDialog.getExistingDirectory(
                self, self.localization['linux.openFolder'], directory, options=QFileDialog.ShowDirsOnly
            )
        elif dialog_type == OPEN_DIALOG:
            if allow_multiple:
                self._file_name = QFileDialog.getOpenFileNames(
                    self, self.localization['linux.openFiles'], directory, file_filter
                )
            else:
                self._file_name = QFileDialog.getOpenFileName(
                    self, self.localization['linux.openFile'], directory, file_filter
                )
        elif dialog_type == SAVE_DIALOG:
            if directory:
                save_filename = os.path.join(str(directory), str(save_filename))

            self._file_name = QFileDialog.getSaveFileName(
                self, self.localization['global.saveFile'], save_filename
            )

        self._file_name_semaphore.release()

    def on_cookie_added(self, cookie):
        raw = str(cookie.toRawForm(), 'utf-8')
        cookie = create_cookie(raw)

        if raw not in self.cookies:
            self.cookies[raw] = cookie

    def on_cookie_removed(self, cookie):
        raw = str(cookie.toRawForm(), 'utf-8')

        if raw in self.cookies:
            del self.cookies[raw]

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
        should_cancel = self.pywebview_window.events.closing.set()

        if should_cancel:
            event.ignore()
            return

        if self.pywebview_window.confirm_close:
            reply = QMessageBox.question(
                self,
                self.title,
                self.localization['global.quitConfirmation'],
                QMessageBox.Yes,
                QMessageBox.No,
            )

            if reply == QMessageBox.No:
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

        if self.windowState() == QtCore.Qt.WindowNoState and e.oldState() in (
            QtCore.Qt.WindowMinimized,
            QtCore.Qt.WindowMaximized,
        ):
            self.pywebview_window.events.restored.set()

    def resizeEvent(self, e):
        if (
            self.pywebview_window.initial_width != self.width()
            or self.pywebview_window.initial_height != self.height()
        ):
            self.pywebview_window.events.resized.set(self.width(), self.height())

    def eventFilter(self, object, event):
        if event.type() == QtCore.QEvent.Move:
            self.pywebview_window.events.moved.set(self.x(), self.y())

        return super().eventFilter(object, event)

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
            js_result['result'] = (
                None
                if result is None or result == 'null'
                else result
                if result == ''
                else json.loads(result)
            )
            js_result['semaphore'].release()

        try:  # < Qt5.6
            if _qt6:
                self.view.page().runJavaScript(script, 0, return_result)
            else:
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
            except:  # QT < 5.6
                self.view.page().mainFrame().evaluateJavaScript(script)

        if _settings['debug']:
            self.view.show_inspector()

    def set_title(self, title):
        self.set_title_trigger.emit(title)

    def get_cookies(self):
        return list(self.cookies.values())

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

    def create_confirmation_dialog(self, title, message):
        result_semaphore = Semaphore(0)
        unique_id = uuid1().hex
        self._confirmation_dialog_results[unique_id] = {
            'semaphore': result_semaphore,
            'result': None,
        }

        self.confirmation_dialog_trigger.emit(title, message, unique_id)
        result_semaphore.acquire()

        result = self._confirmation_dialog_results[unique_id]['result']
        del self._confirmation_dialog_results[unique_id]

        return result

    def create_file_dialog(
        self, dialog_type, directory, allow_multiple, save_filename, file_filter
    ):
        self.file_dialog_trigger.emit(
            dialog_type, directory, allow_multiple, save_filename, file_filter
        )
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

            result = result.toString()  # QJsonValue conversion
        except AttributeError:
            pass

        return str(result)

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


def setup_app():
    # MUST be called before create_window and set_app_menu
    global _app
    _app = QApplication.instance() or QApplication([])


def create_window(window):
    def _create():
        browser = BrowserView(window)
        browser.installEventFilter(browser)

        # If the menu we created as part of set_app_menu was not set as the native menu, then
        #     we need to recreate the menu for every window
        if BrowserView.global_menubar and not BrowserView.global_menubar.isNativeMenuBar():
            window_menubar = browser.menuBar()
            for menu in BrowserView.global_menubar_top_menus:
                window_menubar.addMenu(menu)

        _main_window_created.set()

        if window.maximized:
            browser.showMaximized()
        elif window.minimized:
            # showMinimized does not work on start without showNormal first
            # looks like a bug in QT
            browser.showNormal()
            browser.showMinimized()
        elif not window.hidden:
            browser.show()

    if window.uid == 'master':
        global _app
        _app = QApplication.instance() or QApplication(sys.argv)

        _create()
        _app.exec_()
    else:
        _main_window_created.wait()
        i = list(BrowserView.instances.values())[0]  # arbitrary instance
        i.create_window_trigger.emit(_create)


def set_title(title, uid):
    BrowserView.instances[uid].set_title(title)


def get_cookies(uid):
    return BrowserView.instances[uid].get_cookies()


def get_current_url(uid):
    return BrowserView.instances[uid].get_current_url()


def load_url(url, uid):
    BrowserView.instances[uid].load_url(url)


def load_html(content, base_uri, uid):
    BrowserView.instances[uid].load_html(content, base_uri)


def set_app_menu(app_menu_list):
    """
    Create a custom menu for the app bar menu (on supported platforms).
    Otherwise, this menu is used across individual windows.

    Args:
        app_menu_list ([webview.menu.Menu])
    """

    def create_submenu(title, line_items, supermenu):
        m = supermenu.addMenu(title)
        BrowserView.global_menubar_other_objects.append(m)
        for menu_line_item in line_items:
            if isinstance(menu_line_item, MenuSeparator):
                m.addSeparator()
            elif isinstance(menu_line_item, MenuAction):
                new_action = QAction(menu_line_item.title)
                func = copy(menu_line_item.function)
                new_action.triggered.connect(lambda: Thread(target=func).start())
                m.addAction(new_action)
                BrowserView.global_menubar_other_objects.append(new_action)
            elif isinstance(menu_line_item, Menu):
                create_submenu(menu_line_item.title, menu_line_item.items, m)

        return m

    # If the application menu has already been created, we don't want to do it again
    if (
        len(BrowserView.global_menubar_top_menus) > 0
        or len(BrowserView.global_menubar_other_objects) > 0
    ):
        return

    top_level_menu = QMenuBar()
    top_level_menu.setNativeMenuBar(True)

    BrowserView.global_menubar = top_level_menu

    for app_menu in app_menu_list:
        BrowserView.global_menubar_top_menus.append(
            create_submenu(app_menu.title, app_menu.items, top_level_menu)
        )


def get_active_window():
    active_window = None
    try:
        active_window = _app.activeWindow()
    except:
        return None

    if active_window:
        return active_window.pywebview_window

    return None


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


def create_confirmation_dialog(title, message, uid):
    return BrowserView.instances[uid].create_confirmation_dialog(title, message)


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
    _app = QApplication.instance() or QApplication(sys.argv)
    screens = [Screen(s.geometry().width(), s.geometry().height(), s) for s in _app.screens()]

    return screens


def add_tls_cert(certfile):
    config = QSslConfiguration.defaultConfiguration()
    certs = config.caCertificates()
    cert = QSslCertificate.fromPath(certfile)[0]
    certs.append(cert)
    config.setCaCertificates(certs)
    QSslConfiguration.setDefaultConfiguration(config)
