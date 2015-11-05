"""
(C) 2014-2015 Roman Sirokov
Licensed under BSD license

http://github.com/r0x0r/pywebview/
"""
import threading

import Foundation
import AppKit
import WebKit
import PyObjCTools.AppHelper

from webview import OPEN_DIALOG, FOLDER_DIALOG, SAVE_DIALOG


class BrowserView:
    instance = None
    app = AppKit.NSApplication.sharedApplication()


    class BrowserDelegate(AppKit.NSObject):
        def windowShouldClose_(self, noti):
            print "close event"

        def contextMenuItemsForElement_(self, defaultMenuItems):
            pass

    class AppDelegate(AppKit.NSObject):
        def windowWillClose_(self, notification):
            BrowserView.app.stop_(self)

    class WebKitHost(WebKit.WebView):
        def windowWillClose_(self, notification):
            pass

        def contextMenuItemsForElement2_(self, defaultMenuItems):
            pass

        def performKeyEquivalent_(self, theEvent):
            """
            Handle common hotkey shortcuts as copy/cut/paste/undo/select all/quit
            :param theEvent:
            :return:
            """

            if theEvent.type() == AppKit.NSKeyDown and theEvent.modifierFlags() & AppKit.NSCommandKeyMask:
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
                        BrowserView.app.terminate_(self)

                    return handled

    def __init__(self, title, url, width, height, resizable, fullscreen):
        BrowserView.instance = self

        self._file_name = None
        self._file_name_semaphor = threading.Semaphore(0)

        rect = AppKit.NSMakeRect(100.0, 350.0, width, height)
        window_mask = AppKit.NSTitledWindowMask | AppKit.NSClosableWindowMask | AppKit.NSMiniaturizableWindowMask

        if resizable:
            window_mask = window_mask | AppKit.NSResizableWindowMask

        self.window = AppKit.NSWindow.alloc().\
            initWithContentRect_styleMask_backing_defer_(rect, window_mask, AppKit.NSBackingStoreBuffered, False)
        self.window.setTitle_(title)

        if fullscreen:
            NSWindowCollectionBehaviorFullScreenPrimary = 1 << 7
            newBehavior = self.window.collectionBehavior() | NSWindowCollectionBehaviorFullScreenPrimary
            self.window.setCollectionBehavior_(newBehavior)
            self.window.setCollectionBehavior_(NSWindowCollectionBehaviorFullScreenPrimary)
            self.window.toggleFullScreen_(None)


        self.webkit = BrowserView.WebKitHost.alloc()
        self.webkit.initWithFrame_(rect) #WebKit.WebView.alloc().initWithFrame_(rect)
        self.window.setContentView_(self.webkit)

        self._appDelegate = BrowserView.AppDelegate.alloc().init()
        self._browserDelegate = BrowserView.BrowserDelegate.alloc().init()

        self.window.setDelegate_(self._appDelegate)
        self.webkit.setUIDelegate_(self._browserDelegate)

        self.load_url(url)

        """
        self.webkit = BrowserView.WebKitHost.alloc()
        self.webkit.initWithFrame_(rect)
        self.load_url(url)

        self.window.setContentView_(self.webkit)
        self.myDelegate = BrowserView.AppDelegate.alloc().init()
        self.window.setDelegate_(self.myDelegate)
        """

    def show(self):
        self.window.display()
        self.window.orderFrontRegardless()
        BrowserView.app.run()

    def load_url(self, url):
        def load(url):
            page_url = Foundation.NSURL.URLWithString_(url)
            req = Foundation.NSURLRequest.requestWithURL_(page_url)
            self.webkit.mainFrame().loadRequest_(req)

        self.url = url
        PyObjCTools.AppHelper.callAfter(load, url)

    def create_file_dialog(self, dialog_type, allow_multiple):
        def create_dialog(*args):
            dialog_type = args[0]
            allow_multiple = args[1]

            openDlg = AppKit.NSOpenPanel.openPanel()

            # Enable the selection of files in the dialog.
            openDlg.setCanChooseFiles_(dialog_type != FOLDER_DIALOG)

            # Enable the selection of directories in the dialog.
            openDlg.setCanChooseDirectories_(dialog_type == FOLDER_DIALOG)

            # Enable / disable multiple selection
            openDlg.setAllowsMultipleSelection_(allow_multiple)

            if openDlg.runModalForDirectory_file_(None, None) == AppKit.NSOKButton:
                files = openDlg.filenames()
                self._file_name = files
            else:
                self._file_name = None

            self._file_name_semaphor.release()

        PyObjCTools.AppHelper.callAfter(create_dialog, dialog_type, allow_multiple)

        self._file_name_semaphor.acquire()
        return self._file_name


def create_window(title, url, width, height, resizable, fullscreen):
    """
    Create a WebView window using Cocoa on Mac.
    :param title: Window title
    :param url: URL to load
    :param width: Window width
    :param height: Window height
    :param resizable True if window can be resized, False otherwise
    :return:
    """
    browser = BrowserView(title, url, width, height, resizable, fullscreen)
    browser.show()


def create_file_dialog(dialog_type, allow_multiple):
    if BrowserView.instance is not None:
        return BrowserView.instance.create_file_dialog(dialog_type, allow_multiple)
    else:
        raise Exception("Create a web view window first, before invoking this function")


def load_url(url):
    if BrowserView.instance is not None:
        BrowserView.instance.load_url(url)
    else:
        raise Exception("Create a web view window first, before invoking this function")
