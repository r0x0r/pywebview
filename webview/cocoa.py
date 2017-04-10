"""
(C) 2014-2016 Roman Sirokov and contributors
Licensed under BSD license

http://github.com/r0x0r/pywebview/
"""
import threading

import Foundation
import AppKit
import WebKit
import PyObjCTools.AppHelper
from objc import nil

from webview.localization import localization
from webview import OPEN_DIALOG, FOLDER_DIALOG, SAVE_DIALOG

# This lines allow to load non-HTTPS resources, like a local app as: http://127.0.0.1:5000
bundle = AppKit.NSBundle.mainBundle()
info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
info["NSAppTransportSecurity"] = {"NSAllowsArbitraryLoads": Foundation.YES}


class BrowserView:
    instance = None
    app = AppKit.NSApplication.sharedApplication()

    class AppDelegate(AppKit.NSObject):
        def applicationDidFinishLaunching_(self, notification):
            BrowserView.instance.webview_ready.set()

    class WindowDelegate(AppKit.NSObject):
        def display_confirmation_dialog(self):
            AppKit.NSApplication.sharedApplication()
            AppKit.NSRunningApplication.currentApplication().activateWithOptions_(AppKit.NSApplicationActivateIgnoringOtherApps)
            alert = AppKit.NSAlert.alloc().init()
            alert.addButtonWithTitle_(localization["global.quit"])
            alert.addButtonWithTitle_(localization["global.cancel"])
            alert.setMessageText_(localization["global.quitConfirmation"])
            alert.setAlertStyle_(AppKit.NSWarningAlertStyle)

            if alert.runModal() == AppKit.NSAlertFirstButtonReturn:
                return True
            else:
                return False

        def windowShouldClose_(self, notification):
            if not _confirm_quit or self.display_confirmation_dialog():
                return Foundation.YES
            else:
                return Foundation.NO

        def windowWillClose_(self, notification):
            BrowserView.app.stop_(self)

    class BrowserDelegate(AppKit.NSObject):
        def webView_contextMenuItemsForElement_defaultMenuItems_(self, webview, element, defaultMenuItems):
            return nil

        # Display a JavaScript alert panel containing the specified message
        def webView_runJavaScriptAlertPanelWithMessage_initiatedByFrame_(self, webview, message, frame):
            AppKit.NSRunningApplication.currentApplication().activateWithOptions_(AppKit.NSApplicationActivateIgnoringOtherApps)
            alert = AppKit.NSAlert.alloc().init()
            alert.setInformativeText_(message)
            alert.runModal()

        def webView_printFrameView_(self, webview, frameview):
            """
            This delegate method is invoked when a script or a user wants to print a webpage (e.g. using the Javascript window.print() method)
            :param webview: the webview that sent the message
            :param frameview: the web frame view whose contents to print
            """
            def printView(frameview):
                # check if the view can handle the content without intervention by the delegate
                can_print = frameview.documentViewShouldHandlePrint()

                if can_print:
                    # tell the view to print the content
                    frameview.printDocumentView()
                else:
                    # get an NSPrintOperaion object to print the view
                    info = AppKit.NSPrintInfo.sharedPrintInfo()
                    print_op = frameview.printOperationWithPrintInfo_(info)
                    print_op.runOperation()

            PyObjCTools.AppHelper.callAfter(printView, frameview)

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

                    if keyCode == 7 and hasSelectedText : #cut
                        responder.cut_(self)
                        handled = True
                    elif keyCode == 8 and hasSelectedText:  #copy
                        responder.copy_(self)
                        handled = True
                    elif keyCode == 9:  # paste
                        responder.paste_(self)
                        handled = True
                    elif keyCode == 0:  # select all
                        responder.selectAll_(self)
                        handled = True
                    elif keyCode == 6:  # undo
                        if responder.undoManager().canUndo():
                            responder.undoManager().undo()
                            handled = True
                    elif keyCode == 12:  # quit
                        BrowserView.app.terminate_(self)

                    return handled

    def __init__(self, title, url, width, height, resizable, fullscreen, min_size, webview_ready):
        BrowserView.instance = self

        self._file_name = None
        self._file_name_semaphor = threading.Semaphore(0)
        self._current_url_semaphor = threading.Semaphore(
            0)
        self.webview_ready = webview_ready
        self.is_fullscreen = False

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
        self._windowDelegate = BrowserView.WindowDelegate.alloc().init()
        self._appDelegate = BrowserView.AppDelegate.alloc().init()
        self.webkit.setUIDelegate_(self._browserDelegate)
        self.webkit.setFrameLoadDelegate_(self._browserDelegate)
        self.window.setDelegate_(self._windowDelegate)
        BrowserView.app.setDelegate_(self._appDelegate)

        self.load_url(url)

        # Add the default Cocoa application menu
        self._add_app_menu()
        self._add_view_menu()

        if fullscreen:
            self.toggle_fullscreen()

    def show(self):
        self.window.display()
        self.window.orderFrontRegardless()
        BrowserView.app.run()

    def destroy(self):
        BrowserView.app.stop_(self)

    def toggle_fullscreen(self):
        def toggle():
            if self.is_fullscreen:
                window_behaviour = 1 << 2  # NSWindowCollectionBehaviorManaged
            else:
                window_behaviour = 1 << 7  # NSWindowCollectionBehaviorFullScreenPrimary

            self.window.setCollectionBehavior_(window_behaviour)
            self.window.toggleFullScreen_(None)

        PyObjCTools.AppHelper.callAfter(toggle)
        self.is_fullscreen = not self.is_fullscreen

    def get_current_url(self):
        def get():
            self._current_url = self.webkit.mainFrameURL()
            self._current_url_semaphor.release()

        PyObjCTools.AppHelper.callAfter(get)

        self._current_url_semaphor.acquire()
        return self._current_url

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
                save_dlg.setTitle_(localization["global.saveFile"])

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

        appMenu.addItemWithTitle_action_keyEquivalent_(self._append_app_name(localization["cocoa.menu.about"]), "orderFrontStandardAboutPanel:", "")

        appMenu.addItem_(AppKit.NSMenuItem.separatorItem())

        # Set the 'Services' menu for the app and create an app menu item
        appServicesMenu = AppKit.NSMenu.alloc().init()
        self.app.setServicesMenu_(appServicesMenu)
        servicesMenuItem = appMenu.addItemWithTitle_action_keyEquivalent_(localization["cocoa.menu.services"], nil, "")
        servicesMenuItem.setSubmenu_(appServicesMenu)

        appMenu.addItem_(AppKit.NSMenuItem.separatorItem())

        # Append the 'Hide', 'Hide Others', and 'Show All' menu items
        appMenu.addItemWithTitle_action_keyEquivalent_(self._append_app_name(localization["cocoa.menu.hide"]), "hide:", "h")
        hideOthersMenuItem = appMenu.addItemWithTitle_action_keyEquivalent_(localization["cocoa.menu.hideOthers"], "hideOtherApplications:", "h")
        hideOthersMenuItem.setKeyEquivalentModifierMask_(AppKit.NSAlternateKeyMask | AppKit.NSCommandKeyMask)
        appMenu.addItemWithTitle_action_keyEquivalent_(localization["cocoa.menu.showAll"], "unhideAllApplications:", "")

        appMenu.addItem_(AppKit.NSMenuItem.separatorItem())

        # Append a 'Quit' menu item
        appMenu.addItemWithTitle_action_keyEquivalent_(self._append_app_name(localization["cocoa.menu.quit"]), "terminate:", "q")

    def _add_view_menu(self):
        """
        Create a default View menu that shows 'Enter Full Screen'.
        """
        mainMenu = self.app.mainMenu()

        # Create an View menu and make it a submenu of the main menu
        viewMenu = AppKit.NSMenu.alloc().init()
        viewMenu.setTitle_(localization["cocoa.menu.view"])
        viewMenuItem = AppKit.NSMenuItem.alloc().init()
        viewMenuItem.setSubmenu_(viewMenu)
        mainMenu.addItem_(viewMenuItem)

        # TODO: localization of the Enter fullscreen string has no effect
        fullScreenMenuItem = viewMenu.addItemWithTitle_action_keyEquivalent_(localization["cocoa.menu.fullscreen"], "toggleFullScreen:", "f")
        fullScreenMenuItem.setKeyEquivalentModifierMask_(AppKit.NSControlKeyMask | AppKit.NSCommandKeyMask)


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


def create_window(title, url, width, height, resizable, fullscreen, min_size, confirm_quit, ready_event):
    """
    Create a WebView window using Cocoa on Mac.
    :param title: Window title
    :param url: URL to load
    :param width: Window width
    :param height: Window height
    :param resizable True if window can be resized, False otherwise
    :return:
    """
    global _confirm_quit
    _confirm_quit = confirm_quit

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


def toggle_fullscreen():
    BrowserView.instance.toggle_fullscreen()


def get_current_url():
    return BrowserView.instance.get_current_url()
