import threading
import platform
import sys
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

# a webview object we use to update URL
_browser_view = None

# the name of the function to invoke depending on the platform
_create_window_func = None


# Mac imports
if platform.system() == "Darwin":
    # Import PyObjC modules
    from Foundation import *
    from AppKit import *
    import WebKit
    logger.info("Using Cocoa")
    _create_window_func = "_create_window_mac"

# Linux Qt imports
if platform.system() == "Linux":
    import_error = False
    # Try importing Qt4 modules
    try:
        from PyQt4 import QtCore
        from PyQt4.QtWebKit import QWebView
        from PyQt4.QtGui import QWidget, QVBoxLayout, QApplication, QDialog

        logger.info("Using Qt4")
        _create_window_func = "_create_window_qt"
    except ImportError as e:
        logger.warn("PyQt4 is not found", exc_info=True)
        import_error = True

    # Try importing Qt5 modules
    if import_error:
        import_error = False
        try:
            from PyQt5 import QtCore
            from PyQt5.QtWebKitWidgets import QWebView
            from PyQt5.QtWidgets import QWidget, QVBoxLayout, QApplication

            logger.info("Using Qt5")
            _create_window_func = "_create_window_qt"
        except ImportError as e:
            logger.warn("PyQt5 is not found", exc_info=True)
            import_error = True

    if import_error:
        raise Exception("No suitable GUI framework found")


def load_url(url):
    """
    Load a new URL into a previously created WebView window. This function must be invoked after WebView windows is
    created with create_window(). Otherwise an exception is thrown.
    :param url: url to load
    """

    if platform.system() != "Darwin" and platform.system() != "Linux":
        raise Exception("Unsupported platform. Only Linux and Mac OSX are supported.")

    if _browser_view is not None:
        # For Darwin this reports a threading violation, but still works
        _browser_view.load_url(url)
    else:
        raise Exception("Create a web view window first, before invoking this function")



def create_window(title, url, width=800, height=600, resizable=True):
    """
    Create a web view window using a native GUI. The execution blocks after this function is invoked, so other
    program logic must be executed as a separate thread.
    :param title: Window title
    :param url: URL to load
    :param width: Optional window width (default: 800px)
    :param height: Optional window height (default: 600px)
    :param resizable True if window can be resized, False otherwise. Default is True.
    :return:
    """
    logger.debug("Invoke function: " + _create_window_func)

    if platform.system() == "Darwin" or platform.system() == "Linux":
        globals()[_create_window_func](title, url, width, height, resizable)
    else:
        raise Exception("Unsupported platform. Only Linux and Mac OSX are supported.")



def _create_window_mac(title, url, width, height, resizable):
    """
    Create a WebView window using Cocoa on Mac.
    :param title: Window title
    :param url: URL to load
    :param width: Window width
    :param height: Window height
    :param resizable True if window can be resized, False otherwise
    :return:
    """
    app = NSApplication.sharedApplication()

    class BrowserView(WebKit.WebView):
        def performKeyEquivalent_(self, theEvent):
            """
            Handle common hotkey shortcuts as copy/cut/paste/undo/select all/quit
            :param theEvent:
            :return:
            """

            if theEvent.type() == NSKeyDown and theEvent.modifierFlags() & NSCommandKeyMask:
                responder = self.window().firstResponder()
                keyCode = theEvent.keyCode()

                if responder != None:
                    handled = False
                    range_ = responder.selectedRange()
                    hasSelectedText = len(range_) > 0

                    if keyCode == 7 and hasSelectedText: #cut
                        responder.cut_(self)
                        handled = True
                    elif keyCode== 8 and hasSelectedText: #copy
                        responder.copy_(self)
                        handled = True
                    elif keyCode == 9: # paste
                        responder.paste_(self)
                        handled = True
                    elif keyCode == 0: # select all
                        responder.selectAll_(self)
                        handled = True
                    elif keyCode == 6: # undo
                        if responder.undoManager().canUndo():
                            responder.undoManager().undo()
                            handled = True
                    elif keyCode == 12: # quit
                        app.terminate_(self)

                    return handled

        def load_url(self, url):
            pageurl = Foundation.NSURL.URLWithString_(url)
            req = Foundation.NSURLRequest.requestWithURL_(pageurl)
            self.mainFrame().loadRequest_(req)


    class AppDelegate(NSObject):
        def windowWillClose_(self, notification):
            app.terminate_(self)


    rect = NSMakeRect(100.0, 350.0, width, height)
    window_mask = NSTitledWindowMask | NSClosableWindowMask | NSMiniaturizableWindowMask
    if resizable:
        window_mask = window_mask | NSResizableWindowMask

    window = \
        NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(rect, window_mask, NSBackingStoreBuffered, False)
    window.setTitle_(title)

    global _browser_view
    _browser_view = BrowserView.alloc()
    _browser_view.initWithFrame_(rect)
    _browser_view.load_url(url)

    window.setContentView_(_browser_view)
    myDelegate = AppDelegate.alloc().init()
    window.setDelegate_(myDelegate)
    window.display()
    window.orderFrontRegardless()
    app.run()



def _create_window_qt(title, url, width, height, resizable):
    """
    Create a WebView window with Qt. Works with both Qt 4.x and 5.x.
    :param title: Window title
    :param url: URL to load
    :param width: Window width
    :param height: Window height
    :param resizable True if window can be resized, False otherwise
    :return:
    """
    class BrowserView(QWidget):
        trigger = QtCore.pyqtSignal(str)

        def __init__(self, title, url, width, height):
            super(BrowserView, self).__init__()

            self.resize(width, height)
            self.setWindowTitle(title)

            if not resizable:
                self.setFixedSize(width, height)

            self.view = QWebView(self)
            self.view.setUrl(QtCore.QUrl(url))

            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self.view)

            self.trigger.connect(self._handle_load_url)

        def _handle_load_url(self, url):
            self.view.setUrl(QtCore.QUrl(url))

        def load_url(self, url):
            self.trigger.emit(url)

    app = QApplication(sys.argv)

    global _browser_view
    _browser_view = BrowserView(title, url, width, height)

    # Move window to the center of the screen
    _browser_view.move(QApplication.desktop().availableGeometry().center() - _browser_view.rect().center())
    _browser_view.show()
    sys.exit(app.exec_())


def load():
    import time
    time.sleep(10)
    load_url("http://www.html5zombo.com/")

if __name__ == '__main__':
    t = threading.Thread(target=load)
    #t.start()

    create_window("Test", "http://www.google.com", resizable=True)

