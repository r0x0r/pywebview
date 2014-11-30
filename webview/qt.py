"""
(C) 2014 Roman Sirokov
Licensed under BSD license

http://github.com/r0x0r/pywebview/
"""

import sys
import logging

logger = logging.getLogger(__name__)


# Try importing Qt4 modules
try:
    from PyQt4 import QtCore
    from PyQt4.QtWebKit import QWebView
    from PyQt4.QtGui import QWidget, QMainWindow, QVBoxLayout, QApplication, QDialog

    logger.info("Using Qt4")
except ImportError as e:
    logger.warn("PyQt4 is not found")
    _import_error = True
else:
    _import_error = False


# Try importing Qt5 modules
if _import_error:
    try:
        from PyQt5 import QtCore
        from PyQt5.QtWebKitWidgets import QWebView
        from PyQt5.QtWidgets import QWidget, QMainWindow, QVBoxLayout, QApplication

        logger.info("Using Qt5")
    except ImportError as e:
        logger.warn("PyQt5 is not found")
        _import_error = True
    else:
        _import_error = False


if _import_error:
    raise Exception("This module requires PyQt4 or PyQt5 to work under Linux.")


class BrowserView(QMainWindow):
    instance = None
    trigger = QtCore.pyqtSignal(str)

    def __init__(self, title, url, width, height, resizable, fullscreen):
        super(BrowserView, self).__init__()
        BrowserView.instance = self

        self.resize(width, height)
        self.setWindowTitle(title)

        if not resizable:
            self.setFixedSize(width, height)

        if fullscreen:
            self.showFullScreen()


        self.view = QWebView(self)
        self.view.setUrl(QtCore.QUrl(url))

        #layout = QVBoxLayout(self)
        #self.layout.setContentsMargins(0, 0, 0, 0)
        #self.layout.addWidget(self.view)
        self.setCentralWidget(self.view)
        self.trigger.connect(self._handle_load_url)

        self.move(QApplication.desktop().availableGeometry().center() - self.rect().center())
        self.activateWindow()
        self.raise_()


    def _handle_load_url(self, url):
        self.view.setUrl(QtCore.QUrl(url))

    def load_url(self, url):
        self.trigger.emit(url)



def create_window(title, url, width, height, resizable, fullscreen):
    """
    Create a WebView window with Qt. Works with both Qt 4.x and 5.x.
    :param title: Window title
    :param url: URL to load
    :param width: Window width
    :param height: Window height
    :param resizable True if window can be resized, False otherwise
    :return:
    """

    app = QApplication([])

    browser = BrowserView(title, url, width, height, resizable, fullscreen)
    browser.show()
    sys.exit(app.exec_())


def load_url(url):
    if BrowserView.instance is not None:
        BrowserView.instance.load_url(url)
    else:
        raise Exception("Create a web view window first, before invoking this function")
