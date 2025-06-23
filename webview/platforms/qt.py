import json
import logging
import os
import platform
import socket
import sys
import webbrowser
from copy import copy, deepcopy
from functools import partial
from threading import Event, Semaphore, Thread
from uuid import uuid1

from webview import (FileDialog, _state, windows, settings)
from webview.dom import _dnd_state
from webview.menu import Menu, MenuAction, MenuSeparator
from webview.models import Request
from webview.screen import Screen
from webview.util import DEFAULT_HTML, create_cookie, js_bridge_call, inject_pywebview, environ_append
from webview.window import FixPoint, Window

logger = logging.getLogger('pywebview')

from qtpy import QtCore

logger.debug('Using Qt %s' % QtCore.__version__)

from qtpy import PYQT6, PYSIDE6
from qtpy.QtCore import QJsonValue, QByteArray
from qtpy.QtGui import QColor, QIcon, QScreen
from qtpy.QtWidgets import QAction, QApplication, QFileDialog, QMainWindow, QMenuBar, QMessageBox

try:
    from qtpy.QtNetwork import QSslCertificate, QSslConfiguration
    from qtpy.QtWebChannel import QWebChannel
    from qtpy.QtWebEngineCore import QWebEngineUrlRequestInterceptor
    from qtpy.QtWebEngineWidgets import QWebEnginePage as QWebPage
    from qtpy.QtWebEngineWidgets import QWebEngineProfile, QWebEngineSettings
    from qtpy.QtWebEngineWidgets import QWebEngineView as QWebView

    renderer = 'qtwebengine'
    is_webengine = True
except ImportError:
    from PyQt5 import QtWebKitWidgets
    from PyQt5.QtNetwork import QSslCertificate, QSslConfiguration
    from PyQt5.QtWebKitWidgets import QWebPage, QWebView

    is_webengine = False
    renderer = 'qtwebkit'

if is_webengine and QtCore.QSysInfo.productType() in ['arch', 'manjaro', 'nixos', 'rhel', 'pop']:
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
_profile_storage_path = _state['storage_path'] or os.path.join(os.path.expanduser('~'), '.pywebview')


class BrowserView(QMainWindow):
    instances = {}
    inspector_port = None  # The localhost port at which the Remote debugger listens

    global_menubar_other_objects = []
    global_menubar_top_menus = []

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
    window_maximize_trigger = QtCore.Signal()
    window_minimize_trigger = QtCore.Signal()
    window_restore_trigger = QtCore.Signal()
    current_url_trigger = QtCore.Signal()
    evaluate_js_trigger = QtCore.Signal(str, str)
    on_top_trigger = QtCore.Signal(bool)

    class JSBridge(QtCore.QObject):
        qtype = QtCore.QJsonValue if is_webengine else str

        def __init__(self, parent):
            super(BrowserView.JSBridge, self).__init__()
            self.parent = parent
            self.window = parent.pywebview_window

        @QtCore.Slot(str, qtype, str, result=str)
        def call(self, func_name, param, value_id):
            func_name = BrowserView._convert_string(func_name)
            param = BrowserView._convert_string(param)

            if func_name == '_pywebviewAlert':
                QMessageBox.information(self.parent, 'Message', str(param))
            else:
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

        def dragEnterEvent(self, e):
            if e.mimeData().hasUrls and _dnd_state['num_listeners'] > 0:
                e.acceptProposedAction()

            return super().dragEnterEvent(e)

        def dragMoveEvent(self, e):
            if e.mimeData().hasUrls and _dnd_state['num_listeners'] > 0:
                e.acceptProposedAction()

            return super().dragMoveEvent(e)

        def dropEvent(self, e):
            if e.mimeData().hasUrls and _dnd_state['num_listeners'] > 0:
                files = [
                    (os.path.basename(value.toString()), value.toString().replace('file://', ''))
                    for value
                    in e.mimeData().urls()
                    if value.toString().startswith('file://')
                ]
                _dnd_state['paths'] += files

            return super().dropEvent(e)

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
                parent.frameless and parent.easy_drag and event.buttons().value == 1
            ):  # left button is pressed
                parent.move(event.globalPos() - self.drag_pos)

        def eventFilter(self, object, event):
            if object.parent() == self:
                if event.type() == QtCore.QEvent.MouseMove:
                    self.mouseMoveEvent(event)
                elif event.type() == QtCore.QEvent.MouseButtonPress:
                    self.mousePressEvent(event)

            return False

    class RequestInterceptor(QWebEngineUrlRequestInterceptor):
        def __init__(self, window):
            super().__init__()
            self.window = window

        def interceptRequest(self, info):
            if len(self.window.events.request_sent) == 0:
                return

            url = info.requestUrl().toString()
            method = info.requestMethod()

            if 'httpHeaders' in dir(info):
                headers = {k.data().decode('utf-8'): k.data().decode('utf-8') for k, v in info.httpHeaders().items()}
            else:
                headers = {}

            request = Request(url, method, headers)
            self.window.events.request_sent.set(request)

            if request.headers != headers:
                for key, value in request.headers.items():
                    info.setHttpHeader(QByteArray(key.encode('utf-8')), QByteArray(value.encode('utf-8')))

    # New-window-requests handler for Qt 5.5+ only
    class NavigationHandler(QWebPage):
        def __init__(self, page):
            super().__init__(page.profile())
            self._parent = page.parent

        def acceptNavigationRequest(self, url, type, is_main_frame):
            if settings['OPEN_EXTERNAL_LINKS_IN_BROWSER']:
                webbrowser.open(url.toString(), 2, True)
                return False
            else:
                self._parent.load_url(url.toString())
                return True

    class WebPage(QWebPage):
        def __init__(self, parent=None, profile=None):
            if is_webengine and profile:
                super(BrowserView.WebPage, self).__init__(profile, parent.webview)
            else:
                super(BrowserView.WebPage, self).__init__(parent.webview)

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
                    QWebPage.Feature.MediaAudioCapture,
                    QWebPage.Feature.MediaVideoCapture,
                    QWebPage.Feature.MediaAudioVideoCapture,
                ):
                    self.setFeaturePermission(url, feature, 1) # QWebPage.PermissionGrantedByUser
                else:
                    self.setFeaturePermission(url, feature, 2) # QWebPage.PermissionDeniedByUser
        else:

            def acceptNavigationRequest(self, frame, request, type):
                if frame is None:
                    webbrowser.open(request.url().toString(), 2, True)
                    return False
                return True

        def userAgentForUrl(self, url):
            user_agent = _state['user_agent']
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
        self.pywebview_window.native = self

        self.js_bridge = BrowserView.JSBridge(self)

        self.is_fullscreen = False

        self._file_name_semaphore = Semaphore(0)
        self._current_url_semaphore = Semaphore(0)

        self.localization = window.localization

        if window.screen:
            if _qt6:
                self.screen = QScreen.geometry(window.screen.frame)
            else:
                self.screen = window.screen.frame.geometry()
        else:
            if _qt6:
                self.screen = QScreen.geometry(QApplication.primaryScreen())
            else:
                self.screen = QApplication.primaryScreen().geometry()

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
        self.setAcceptDrops(True)

        self.transparent = window.transparent
        if self.transparent:
            # Override the background color
            self.background_color = QColor('transparent')
            palette = self.palette()
            palette.setColor(self.backgroundRole(), self.background_color)
            self.setPalette(palette)
            # Enable the transparency hint
            self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.webview = BrowserView.WebView(self)

        if is_webengine:
            environ_append(
                'QTWEBENGINE_CHROMIUM_FLAGS',
                '--use-fake-ui-for-media-stream',
                '--enable-features=AutoplayIgnoreWebAudio',
            )

        if _state['debug'] and is_webengine:
            # Initialise Remote debugging (need to be done only once)
            if not BrowserView.inspector_port:
                BrowserView.inspector_port = BrowserView._get_debug_port()
                os.environ['QTWEBENGINE_REMOTE_DEBUGGING'] = BrowserView.inspector_port
        else:
            self.webview.setContextMenuPolicy(
                QtCore.Qt.NoContextMenu
            )  # disable right click context menu

        self.cookies = {}

        if is_webengine:
            self.request_interceptor = BrowserView.RequestInterceptor(self.pywebview_window)

            if _state['private_mode']:
                self.profile = QWebEngineProfile()
            else:
                self.profile = QWebEngineProfile('pywebview')
                self.profile.setPersistentStoragePath(_profile_storage_path)

            user_agent = _state['user_agent']
            if user_agent:
                self.profile.setHttpUserAgent(user_agent)

            cookie_store = self.profile.cookieStore()
            cookie_store.cookieAdded.connect(self.on_cookie_added)
            cookie_store.cookieRemoved.connect(self.on_cookie_removed)

            self.profile.setUrlRequestInterceptor(self.request_interceptor)
            self.webview.setPage(BrowserView.WebPage(self, profile=self.profile))
        elif not is_webengine and not _state['private_mode']:
            logger.warning('qtwebkit does not support private_mode')

        user_agent = _state['user_agent']
        # if user_agent and is_webengine:
        #     self.profile.setHttpUserAgent(user_agent)

        if is_webengine:
            self.profile.settings().setAttribute(
                QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, settings['ALLOW_FILE_URLS'])

        self.webview.page().loadFinished.connect(self.on_load_finished)

        if settings['ALLOW_DOWNLOADS']:
            self.webview.page().profile().downloadRequested.connect(self.on_download_requested)

        self.setCentralWidget(self.webview)

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
        self.window_maximize_trigger.connect(self.on_window_maximize)
        self.window_minimize_trigger.connect(self.on_window_minimize)
        self.window_restore_trigger.connect(self.on_window_restore)
        self.current_url_trigger.connect(self.on_current_url)
        self.evaluate_js_trigger.connect(self.on_evaluate_js)
        self.set_title_trigger.connect(self.on_set_title)
        self.on_top_trigger.connect(self.on_set_on_top)

        if is_webengine and platform.system() != 'OpenBSD':
            self.channel = QWebChannel(self.webview.page())
            self.webview.page().setWebChannel(self.channel)

        if window.fullscreen:
            self.toggle_fullscreen()

        if window.real_url is not None:
            self.webview.setUrl(QtCore.QUrl(window.real_url))
        elif window.uid == 'web_inspector':
            self.webview.setUrl(QtCore.QUrl(window.original_url))
        elif window.html:
            self.webview.setHtml(window.html, QtCore.QUrl(''))
        else:
            self.webview.setHtml(DEFAULT_HTML, QtCore.QUrl(''))

        if window.initial_x is not None and window.initial_y is not None:
            self.move(self.screen.x()+window.initial_x, self.screen.y()+window.initial_y)
        else:
            offset = -16 if _qt6 else 0
            center = self.screen.center() - self.rect().center()
            self.move(center.x(), center.y()+offset)

        if not window.minimized:
            self.activateWindow()
            self.raise_()

        if _state['icon']:
            icon = QIcon(_state['icon'])
            self.setWindowIcon(icon)

        self.pywebview_window.events.before_show.set()

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
        if dialog_type == FileDialog.FOLDER:
            self._file_name = QFileDialog.getExistingDirectory(
                self, self.localization['linux.openFolder'], directory, options=QFileDialog.ShowDirsOnly
            )
        elif dialog_type == FileDialog.OPEN:
            if allow_multiple:
                self._file_name = QFileDialog.getOpenFileNames(
                    self, self.localization['linux.openFiles'], directory, file_filter
                )
            else:
                self._file_name = QFileDialog.getOpenFileName(
                    self, self.localization['linux.openFile'], directory, file_filter
                )
        elif dialog_type == FileDialog.SAVE:
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
        url = BrowserView._convert_string(self.webview.url().toString())
        self._current_url = None if url == '' or url.startswith('data:text/html') else url
        self._current_url_semaphore.release()

    def on_load_url(self, url):
        self.webview.setUrl(QtCore.QUrl(url))

    def on_load_html(self, content, base_uri):
        self.webview.setHtml(content, QtCore.QUrl(base_uri))

    def on_set_on_top(self, top):
        flags = self.windowFlags()
        if top:
            self.setWindowFlags(flags | QtCore.Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~QtCore.Qt.WindowStaysOnTopHint)

        self.show()

    def showEvent(self, event):
        self.pywebview_window.events.shown.set()

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

        del BrowserView.instances[self.uid]
        self.close()

        if self.pywebview_window in windows:
            windows.remove(self.pywebview_window)

        self.pywebview_window.events.closed.set()

        if self.webview.page():
            self.webview.page().deleteLater()

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

    def on_window_maximize(self):
        self.setWindowState(QtCore.Qt.WindowMaximized)

    def on_window_minimize(self):
        self.setWindowState(QtCore.Qt.WindowMinimized)

    def on_window_restore(self):
        self.setWindowState(QtCore.Qt.WindowNoState)
        self.raise_()
        self.activateWindow()

    def on_evaluate_js(self, script, uuid):
        def return_result(result_):
            result = BrowserView._convert_string(result_)
            uuid_ = BrowserView._convert_string(uuid)

            js_result = self._js_results[uuid_]

            if js_result['parse_json'] and result:
                try:
                    js_result['result'] = json.loads(result)
                except Exception:
                    logger.exception('Failed to parse JSON: %s', result)
                    js_result['result'] = result
            else:
                js_result['result'] = result

            js_result['semaphore'].release()

        try:  # < Qt5.6
            if _qt6:
                self.webview.page().runJavaScript(script, 0, return_result)
            else:
                self.webview.page().runJavaScript(script, return_result)
        except TypeError:
            self.webview.page().runJavaScript(script)  # PySide2 & PySide6
        except AttributeError:
            result = self.webview.page().mainFrame().evaluateJavaScript(script)
            return_result(result)
        except Exception as e:
            logger.exception(e)

    def on_load_finished(self):
        if self.uid == 'web_inspector':
            return

        self._set_js_api()

        if _state['debug'] and settings['OPEN_DEVTOOLS_IN_DEBUG']:
            self.webview.show_inspector()

    def on_download_requested(self, download):
        old_path = download.url().path()
        suffix = QtCore.QFileInfo(old_path).suffix()
        path, _ = QFileDialog.getSaveFileName(
            self, self.localization['global.saveFile'], old_path, "*." + suffix
        )
        if path:
            download.setPath(path)
            download.accept()

    def set_title(self, title):
        self.set_title_trigger.emit(title)

    def get_cookies(self):
        return list(self.cookies.values())

    def clear_cookies(self):
        self.cookies = {}
        self.profile.cookieStore().deleteAllCookies()

    def get_current_url(self):
        self.current_url_trigger.emit()
        self._current_url_semaphore.acquire()

        return self._current_url

    def load_url(self, url):
        self.load_url_trigger.emit(url)

    def load_html(self, content, base_uri):
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

        if dialog_type == FileDialog.FOLDER:
            file_names = (self._file_name,)
        elif dialog_type == FileDialog.SAVE or not allow_multiple:
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

    def maximize(self):
        self.window_maximize_trigger.emit()

    def minimize(self):
        self.window_minimize_trigger.emit()

    def restore(self):
        self.window_restore_trigger.emit()

    def set_on_top(self, top):
        self.on_top_trigger.emit(top)

    def evaluate_js(self, script, parse_json):
        result_semaphore = Semaphore(0)
        unique_id = uuid1().hex
        self._js_results[unique_id] = {'semaphore': result_semaphore, 'result': '', 'parse_json': parse_json }

        self.evaluate_js_trigger.emit(script, unique_id)
        result_semaphore.acquire()

        result = deepcopy(self._js_results[unique_id]['result'])
        del self._js_results[unique_id]

        return result

    def _set_js_api(self):
        def _register_window_object():
            frame.addToJavaScriptWindowObject('external', self.js_bridge)

        if is_webengine:
            qwebchannel_js = QtCore.QFile('://qtwebchannel/qwebchannel.js')
            if qwebchannel_js.open(QtCore.QFile.ReadOnly):
                source = bytes(qwebchannel_js.readAll()).decode('utf-8')
                self.webview.page().runJavaScript(source)
                self.channel.registerObject('external', self.js_bridge)
                qwebchannel_js.close()
        else:
            frame = self.webview.page().mainFrame()
            _register_window_object()

        inject_pywebview(renderer, self.js_bridge.window)

    @staticmethod
    def _convert_string(result):
        if isinstance(result, QJsonValue):
            return None if result.isNull() else result.toString()
        else:
            return result

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
    global _app
    if settings['IGNORE_SSL_ERRORS']:
        environ_append('QTWEBENGINE_CHROMIUM_FLAGS', '--ignore-certificate-errors')
    _app = QApplication.instance() or QApplication(sys.argv)


def create_window(window):
    def _create():
        browser = BrowserView(window)
        browser.installEventFilter(browser)

        if window.menu or _app_menu:
            menu = window.menu or _state['menu']
            window_menubar = browser.menuBar()
            create_menu(menu, window_menubar)

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
        elif window.hidden:
            browser.pywebview_window.events.shown.set()

    if window.uid == 'master':
        global _app, _app_menu
        if _state['menu']:
            _app_menu = QMenuBar()
            _app_menu.setNativeMenuBar(False)
            create_menu(_state['menu'], _app_menu)
        else:
            _app_menu = None

        _app = QApplication.instance() or QApplication(sys.argv)

        _create()
        _app.exec_()
    else:
        _main_window_created.wait()
        i = list(BrowserView.instances.values())[0]  # arbitrary instance
        i.create_window_trigger.emit(_create)


def set_title(title, uid):
    i = BrowserView.instances.get(uid)
    if i:
        i.set_title(title)


def clear_cookies(uid):
    i = BrowserView.instances.get(uid)
    if i:
        i.clear_cookies()


def get_cookies(uid):
    i = BrowserView.instances.get(uid)
    if i:
        return i.get_cookies()


def get_current_url(uid):
    i = BrowserView.instances.get(uid)
    if i:
        return i.get_current_url()


def load_url(url, uid):
    i = BrowserView.instances.get(uid)
    if i:
        i.load_url(url)


def load_html(content, base_uri, uid):
    i = BrowserView.instances.get(uid)
    if i:
        i.load_html(content, base_uri)


def create_menu(app_menu_list, menubar):
    """
    Create the menu bar for the application for the provided QMenuBar object. Menu can be either a global
    application menu or a window-specific menu.

    Args:
        app_menu_list ([webview.menu.Menu])
        menubar (QMenuBar)
    """
    def run_action(func):
        Thread(target=func).start()

    def create_submenu(title, line_items, supermenu):
        m = supermenu.addMenu(title)
        BrowserView.global_menubar_other_objects.append(m)
        for menu_line_item in line_items:
            if isinstance(menu_line_item, MenuSeparator):
                m.addSeparator()
            elif isinstance(menu_line_item, MenuAction):
                new_action = QAction(menu_line_item.title)
                func = copy(menu_line_item.function)
                new_action.triggered.connect(partial(run_action, func))
                m.addAction(new_action)
                BrowserView.global_menubar_other_objects.append(new_action)
            elif isinstance(menu_line_item, Menu):
                create_submenu(menu_line_item.title, menu_line_item.items, m)

        return m

    for app_menu in app_menu_list:
        menu = create_submenu(app_menu.title, app_menu.items, menubar)
        menubar.addMenu(menu)


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
    i = BrowserView.instances.get(uid)
    if i:
        i.destroy_()


def hide(uid):
    i = BrowserView.instances.get(uid)
    if i:
        i.hide_()


def show(uid):
    i = BrowserView.instances.get(uid)
    if i:
        i.show_()


def maximize(uid):
    i = BrowserView.instances.get(uid)
    if i:
        i.maximize()


def minimize(uid):
    i = BrowserView.instances.get(uid)
    if i:
        i.minimize()


def restore(uid):
    i = BrowserView.instances.get(uid)
    if i:
        i.restore()


def toggle_fullscreen(uid):
    i = BrowserView.instances.get(uid)
    if i:
        i.toggle_fullscreen()


def set_on_top(uid, top):
    i = BrowserView.instances.get(uid)
    if i:
        i.set_on_top(top)


def resize(width, height, uid, fix_point):
    i = BrowserView.instances.get(uid)
    if i:
        i.resize_(width, height, fix_point)


def move(x, y, uid):
    i = BrowserView.instances.get(uid)
    if i:
        i.move_window(x, y)


def create_confirmation_dialog(title, message, uid):
    i = BrowserView.instances.get(uid)
    if i:
        return i.create_confirmation_dialog(title, message)


def create_file_dialog(dialog_type, directory, allow_multiple, save_filename, file_types, uid):
    # Create a file filter by parsing allowed file types
    file_types = [s.replace(';', ' ') for s in file_types]
    file_filter = ';;'.join(file_types)

    i = BrowserView.instances.get(uid)
    if i:
        return i.create_file_dialog(dialog_type, directory, allow_multiple, save_filename, file_filter)


def evaluate_js(script, uid, parse_json=True):
    i = BrowserView.instances.get(uid)
    if i:
        return i.evaluate_js(script, parse_json)


def get_position(uid):
    i = BrowserView.instances.get(uid)
    if i:
        position = i.geometry()
        return position.x(), position.y()
    else:
        return None, None


def get_size(uid):
    i = BrowserView.instances.get(uid)
    if i:
        return i.width(), i.height()
    else:
        return None, None


def get_screens():
    global _app
    _app = QApplication.instance() or QApplication(sys.argv)
    screens = [Screen(s.geometry().x(), s.geometry().y(), s.geometry().width(), s.geometry().height(), s) for s in _app.screens()]

    return screens


def add_tls_cert(certfile):
    config = QSslConfiguration.defaultConfiguration()
    certs = config.caCertificates()
    cert = QSslCertificate.fromPath(certfile)[0]
    certs.append(cert)
    config.setCaCertificates(certs)
    QSslConfiguration.setDefaultConfiguration(config)
