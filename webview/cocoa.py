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

        def webView_didFinishLoadForFrame_(self, webview, frame):
            BrowserView.instance.webview_ready.set()

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

    def __init__(self, title, url, width, height, resizable, fullscreen, min_size, webview_ready):
        BrowserView.instance = self

        self._file_name = None
        self._file_name_semaphor = threading.Semaphore(0)
        self.webview_ready = webview_ready

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
        self.webkit.setFrameLoadDelegate_(self._browserDelegate)
        self.window.setDelegate_(self._appDelegate)

        self.load_url(url)

        # Add the default Cocoa application menu
        self._add_app_menu()

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

    def load_html(self, content, base_uri):
        def load(content, url):
            url = Foundation.NSURL.URLWithString_(url)
            self.webkit.mainFrame().loadHTMLString_baseURL_(content, url)

        PyObjCTools.AppHelper.callAfter(load, content, base_uri)

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

    def _add_app_menu(self):
        """
        Create a default Cocoa menu that shows 'Services', 'Hide',
        'Hide Others', 'Show All', and 'Quit'. Will append the application name
        to some menu items if it's available.
        """
        # Set the main menu for the application
        mainMenu = AppKit.NSMenu.alloc().init()
        self.app.setMainMenu_(mainMenu)

        # Create an application menu and make it a submenu of the main menu
        mainAppMenuItem = AppKit.NSMenuItem.alloc().init()
        mainMenu.addItem_(mainAppMenuItem)
        appMenu = AppKit.NSMenu.alloc().init()
        mainAppMenuItem.setSubmenu_(appMenu)

        # Set the 'Services' menu for the app and create an app menu item
        appServicesMenu = AppKit.NSMenu.alloc().init()
        self.app.setServicesMenu_(appServicesMenu)
        servicesMenuItem = appMenu.addItemWithTitle_action_keyEquivalent_("Services", nil, "")
        servicesMenuItem.setSubmenu_(appServicesMenu)

        appMenu.addItem_(AppKit.NSMenuItem.separatorItem())

        # Append the 'Hide', 'Hide Others', and 'Show All' menu items
        appMenu.addItemWithTitle_action_keyEquivalent_(self._append_app_name('Hide'), 'hide:', 'h')
        hideOthersMenuItem = appMenu.addItemWithTitle_action_keyEquivalent_('Hide Others', 'hideOtherApplications:', 'h')
        hideOthersMenuItem.setKeyEquivalentModifierMask_(AppKit.NSAlternateKeyMask | AppKit.NSCommandKeyMask)
        appMenu.addItemWithTitle_action_keyEquivalent_('Show All', 'unhideAllApplications:', '')

        appMenu.addItem_(AppKit.NSMenuItem.separatorItem())

        # Append a 'Quit' menu item
        appMenu.addItemWithTitle_action_keyEquivalent_(self._append_app_name('Quit'), "terminate:", "q")

    def _append_app_name(self, val):
        """
        Append the application name to a string if it's available. If not, the
        string is returned unchanged.

        :param str val: The string to append to
        :return: String with app name appended, or unchanged string
        :rtype: str
        """
        if "CFBundleName" in info:
            val += " {}".format(info["CFBundleName"])
        return val


def create_window(title, url, width, height, resizable, fullscreen, min_size, ready_event):
    """
    Create a WebView window using Cocoa on Mac.
    :param title: Window title
    :param url: URL to load
    :param width: Window width
    :param height: Window height
    :param resizable True if window can be resized, False otherwise
    :return:
    """
    browser = BrowserView(title, url, width, height, resizable, fullscreen, min_size, ready_event)
    browser.show()


def create_file_dialog(dialog_type, directory, allow_multiple, save_filename):
    return BrowserView.instance.create_file_dialog(dialog_type, directory, allow_multiple, save_filename)


def load_url(url):
    BrowserView.instance.load_url(url)

def load_html(content, base_uri):
    BrowserView.instance.load_html(content, base_uri)

def destroy_window():
    BrowserView.instance.destroy()
