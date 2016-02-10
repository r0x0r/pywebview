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
from objc import nil

from webview import OPEN_DIALOG, FOLDER_DIALOG, SAVE_DIALOG

# This lines allow to load non-HTTPS resources, like a local app as: http://127.0.0.1:5000
bundle = AppKit.NSBundle.mainBundle()
info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
info['NSAppTransportSecurity'] = {'NSAllowsArbitraryLoads': Foundation.YES}


class BrowserView:
    instance = None
    app = AppKit.NSApplication.sharedApplication()

    class AppDelegate(AppKit.NSObject):
        def windowWillClose_(self, notification):
            BrowserView.app.stop_(self)

    class BrowserDelegate(AppKit.NSObject):
        def webView_contextMenuItemsForElement_defaultMenuItems_(self, webview, element, defaultMenuItems):
            return nil

    class WebKitHost(WebKit.WebView):
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

    def __init__(self, title, url, width, height, resizable, fullscreen, min_size):
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
        self.window.setMinSize_(AppKit.NSSize(min_size[0], min_size[1]))

        self.webkit = BrowserView.WebKitHost.alloc().initWithFrame_(rect)
        self.window.setContentView_(self.webkit)

        self._browserDelegate = BrowserView.BrowserDelegate.alloc().init()
        self._appDelegate = BrowserView.AppDelegate.alloc().init()
        self.webkit.setUIDelegate_(self._browserDelegate)
        self.window.setDelegate_(self._appDelegate)

        self.load_url(url)

        if fullscreen:
            NSWindowCollectionBehaviorFullScreenPrimary = 128
            self.window.setCollectionBehavior_(NSWindowCollectionBehaviorFullScreenPrimary)
            self.window.toggleFullScreen_(None)

    def show(self):
        self.window.display()
        self.window.orderFrontRegardless()
        BrowserView.app.run()

    def destroy(self):
        BrowserView.app.stop_(self)

    def load_url(self, url):
        def load(url):
            page_url = Foundation.NSURL.URLWithString_(url)
            req = Foundation.NSURLRequest.requestWithURL_(page_url)
            self.webkit.mainFrame().loadRequest_(req)

        self.url = url
        PyObjCTools.AppHelper.callAfter(load, url)

    def create_file_dialog(self, dialog_type, directory, allow_multiple, save_filename):
        def create_dialog(*args):
            dialog_type = args[0]

            if dialog_type == SAVE_DIALOG:
                save_filename = args[2]

                save_dlg = AppKit.NSSavePanel.savePanel()
                save_dlg.setTitle_("Save file")

                if directory:  # set initial directory
                    save_dlg.setDirectoryURL_(Foundation.NSURL.fileURLWithPath_(directory))

                if save_filename:  # set file name
                    save_dlg.setNameFieldStringValue_(save_filename)

                if save_dlg.runModal() == AppKit.NSFileHandlingPanelOKButton:
                    file = save_dlg.filenames()
                    self._file_name = tuple(file)
                else:
                    self._file_name = None
            else:
                allow_multiple = args[1]

                open_dlg = AppKit.NSOpenPanel.openPanel()

                # Enable the selection of files in the dialog.
                open_dlg.setCanChooseFiles_(dialog_type != FOLDER_DIALOG)

                # Enable the selection of directories in the dialog.
                open_dlg.setCanChooseDirectories_(dialog_type == FOLDER_DIALOG)

                # Enable / disable multiple selection
                open_dlg.setAllowsMultipleSelection_(allow_multiple)

                if directory:  # set initial directory
                    open_dlg.setDirectoryURL_(Foundation.NSURL.fileURLWithPath_(directory))

                if open_dlg.runModal() == AppKit.NSFileHandlingPanelOKButton:
                    files = open_dlg.filenames()
                    self._file_name = tuple(files)
                else:
                    self._file_name = None

            self._file_name_semaphor.release()

        PyObjCTools.AppHelper.callAfter(create_dialog, dialog_type, allow_multiple, save_filename)

        self._file_name_semaphor.acquire()
        return self._file_name


def create_window(title, url, width, height, resizable, fullscreen, min_size):
    """
    Create a WebView window using Cocoa on Mac.
    :param title: Window title
    :param url: URL to load
    :param width: Window width
    :param height: Window height
    :param resizable True if window can be resized, False otherwise
    :return:
    """
    browser = BrowserView(title, url, width, height, resizable, fullscreen, min_size)
    browser.show()


def create_file_dialog(dialog_type, directory, allow_multiple, save_filename):
    if BrowserView.instance is not None:
        return BrowserView.instance.create_file_dialog(dialog_type, directory, allow_multiple, save_filename)
    else:
        raise Exception("Create a web view window first, before invoking this function")


def load_url(url):
    if BrowserView.instance is not None:
        BrowserView.instance.load_url(url)
    else:
        raise Exception("Create a web view window first, before invoking this function")


def destroy_window():
    if BrowserView.instance is not None:
        BrowserView.instance.destroy()
    else:
        raise Exception("Create a web view window first, before invoking this function")
