"""
(C) 2014-2016 Roman Sirokov and contributors
Licensed under BSD license

http://github.com/r0x0r/pywebview/
"""
import sys
import subprocess
from threading import Event, Semaphore

import Foundation
import AppKit
import WebKit
import PyObjCTools.AppHelper
from objc import nil, super

from webview.localization import localization
from webview import OPEN_DIALOG, FOLDER_DIALOG, SAVE_DIALOG
from webview import _parse_file_type, _js_bridge_call, _parse_api_js

# This lines allow to load non-HTTPS resources, like a local app as: http://127.0.0.1:5000
bundle = AppKit.NSBundle.mainBundle()
info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
info['NSAppTransportSecurity'] = {'NSAllowsArbitraryLoads': Foundation.YES}


class BrowserView:
    instances = {}
    app = AppKit.NSApplication.sharedApplication()
    debug = False
    cascade_loc = Foundation.NSMakePoint(100.0, 0.0)

    class AppDelegate(AppKit.NSObject):
        def applicationDidFinishLaunching_(self, notification):
            i = list(BrowserView.instances.values())[0]
            i.webview_ready.set()

        def applicationShouldTerminateAfterLastWindowClosed_(self, sender):
            return Foundation.YES

    class WindowDelegate(AppKit.NSObject):
        def windowShouldClose_(self, window):
            i = BrowserView.get_instance('window', window)

            quit = localization['global.quit']
            cancel = localization['global.cancel']
            msg = localization['global.quitConfirmation']

            if not i.confirm_quit or BrowserView.display_confirmation_dialog(quit, cancel, msg):
                return Foundation.YES
            else:
                return Foundation.NO

        def windowWillClose_(self, notification):
            # Delete the closed instance from the dict
            i = BrowserView.get_instance('window', notification.object())
            del BrowserView.instances[i.uid]

    class JSBridge(AppKit.NSObject):
        def initWithObject_(self, api_instance):
            super(BrowserView.JSBridge, self).init()
            self.api = api_instance
            return self

        def callFunc_withParam_(self, func_name, param):
            if param is WebKit.WebUndefined.undefined():
                param = None

            i = BrowserView.get_instance('js_bridge', self)
            _js_bridge_call(i.uid, self.api, func_name, param)

        def isSelectorExcludedFromWebScript_(self, selector):
            return Foundation.NO if selector == 'callFunc:withParam:' else Foundation.YES

        @classmethod
        def webScriptNameForSelector_(cls, selector):
            return 'call' if selector == 'callFunc:withParam:' else None

    class BrowserDelegate(AppKit.NSObject):
        def webView_contextMenuItemsForElement_defaultMenuItems_(self, webview, element, defaultMenuItems):
            if BrowserView.debug:
                return defaultMenuItems
            else:
                return nil

        # Display a JavaScript alert panel containing the specified message
        def webView_runJavaScriptAlertPanelWithMessage_initiatedByFrame_(self, webview, message, frame):
            AppKit.NSRunningApplication.currentApplication().activateWithOptions_(AppKit.NSApplicationActivateIgnoringOtherApps)
            alert = AppKit.NSAlert.alloc().init()
            alert.setInformativeText_(message)
            alert.runModal()

        # Display a JavaScript confirm panel containing the specified message
        def webView_runJavaScriptConfirmPanelWithMessage_initiatedByFrame_(self, webview, message, frame):
            ok = localization['global.ok']
            cancel = localization['global.cancel']

            if BrowserView.display_confirmation_dialog(ok, cancel, message):
                return Foundation.YES
            else:
                return Foundation.NO

        # Display an open panel for <input type="file"> element
        def webView_runOpenPanelForFileButtonWithResultListener_allowMultipleFiles_(self, webview, listener, allow_multiple):
            i = list(BrowserView.instances.values())[0]
            files = i.create_file_dialog(OPEN_DIALOG, '', allow_multiple, '', [], main_thread=True)

            if files:
                listener.chooseFilenames_(files)
            else:
                listener.cancel()

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
                    info = AppKit.NSPrintInfo.sharedPrintInfo().copy()

                    # default print settings used by Safari
                    info.setHorizontalPagination_(AppKit.NSFitPagination)
                    info.setHorizontallyCentered_(Foundation.NO)
                    info.setVerticallyCentered_(Foundation.NO)

                    imageableBounds = info.imageablePageBounds()
                    paperSize = info.paperSize()
                    if (Foundation.NSWidth(imageableBounds) > paperSize.width):
                        imageableBounds.origin.x = 0
                        imageableBounds.size.width = paperSize.width
                    if (Foundation.NSHeight(imageableBounds) > paperSize.height):
                        imageableBounds.origin.y = 0
                        imageableBounds.size.height = paperSize.height

                    info.setBottomMargin_(Foundation.NSMinY(imageableBounds))
                    info.setTopMargin_(paperSize.height - Foundation.NSMinY(imageableBounds) - Foundation.NSHeight(imageableBounds))
                    info.setLeftMargin_(Foundation.NSMinX(imageableBounds))
                    info.setRightMargin_(paperSize.width - Foundation.NSMinX(imageableBounds) - Foundation.NSWidth(imageableBounds))

                    # show the print panel
                    print_op = frameview.printOperationWithPrintInfo_(info)
                    print_op.runOperation()

            PyObjCTools.AppHelper.callAfter(printView, frameview)

        # WebPolicyDelegate method, invoked when a navigation decision needs to be made
        def webView_decidePolicyForNavigationAction_request_frame_decisionListener_(self, webview, action, request, frame, listener):
            # The event that might have triggered the navigation
            event = AppKit.NSApp.currentEvent()
            action_type = action['WebActionNavigationTypeKey'] 

            """ Disable back navigation on pressing the Delete key: """
            # Check if the requested navigation action is Back/Forward
            if action_type == WebKit.WebNavigationTypeBackForward:
                # Check if the event is a Delete key press (keyCode = 51)
                if event and event.type() == AppKit.NSKeyDown and event.keyCode() == 51:
                    # If so, ignore the request and return
                    listener.ignore()
                    return

            # Normal navigation, allow
            listener.use()

        # Show the webview when it finishes loading
        def webView_didFinishLoadForFrame_(self, webview, frame):
            # Add the webview to the window if it's not yet the contentView
            i = BrowserView.get_instance('webkit', webview)

            if not webview.window():
                i.window.setContentView_(webview)
                i.window.makeFirstResponder_(webview)

                if i.js_bridge:
                    i._set_js_api()

            i.loaded.set()

    class FileFilterChooser(AppKit.NSPopUpButton):
        def initWithFilter_(self, file_filter):
            super(BrowserView.FileFilterChooser, self).init()
            self.filter = file_filter

            self.addItemsWithTitles_([i[0] for i in self.filter])
            self.setAction_('onChange:')
            self.setTarget_(self)
            return self

        def onChange_(self, sender):
            option = sender.indexOfSelectedItem()
            self.window().setAllowedFileTypes_(self.filter[option][1])

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

    def __init__(self, uid, title, url, width, height, resizable, fullscreen, min_size,
                 confirm_quit, background_color, debug, js_api, webview_ready):
        BrowserView.instances[uid] = self
        self.uid = uid

        if debug:
            BrowserView.debug = debug
            BrowserView._set_debugging()

        self.js_bridge = None
        self._file_name = None
        self._file_name_semaphore = Semaphore(0)
        self._current_url_semaphore = Semaphore(0)
        self.webview_ready = webview_ready
        self.loaded = Event()
        self.confirm_quit = confirm_quit
        self.title = title

        self.is_fullscreen = False

        rect = AppKit.NSMakeRect(0.0, 0.0, width, height)
        window_mask = AppKit.NSTitledWindowMask | AppKit.NSClosableWindowMask | AppKit.NSMiniaturizableWindowMask

        if resizable:
            window_mask = window_mask | AppKit.NSResizableWindowMask

        # The allocated resources are retained because we would explicitly delete
        # this instance when its window is closed
        self.window = AppKit.NSWindow.alloc().\
            initWithContentRect_styleMask_backing_defer_(rect, window_mask, AppKit.NSBackingStoreBuffered, False).retain()
        self.window.setTitle_(title)
        self.window.setBackgroundColor_(BrowserView.nscolor_from_hex(background_color))
        self.window.setMinSize_(AppKit.NSSize(min_size[0], min_size[1]))
        BrowserView.cascade_loc = self.window.cascadeTopLeftFromPoint_(BrowserView.cascade_loc)
        # Set the titlebar color (so that it does not change with the window color)
        self.window.contentView().superview().subviews().lastObject().setBackgroundColor_(AppKit.NSColor.windowBackgroundColor())

        self.webkit = BrowserView.WebKitHost.alloc().initWithFrame_(rect).retain()

        self._browserDelegate = BrowserView.BrowserDelegate.alloc().init().retain()
        self._windowDelegate = BrowserView.WindowDelegate.alloc().init().retain()
        self._appDelegate = BrowserView.AppDelegate.alloc().init().retain()
        self.webkit.setUIDelegate_(self._browserDelegate)
        self.webkit.setFrameLoadDelegate_(self._browserDelegate)
        self.webkit.setPolicyDelegate_(self._browserDelegate)
        self.window.setDelegate_(self._windowDelegate)
        BrowserView.app.setDelegate_(self._appDelegate)

        if url:
            self.url = url
            self.load_url(url)

        if js_api:
            self.js_bridge = BrowserView.JSBridge.alloc().initWithObject_(js_api)

        if fullscreen:
            self.toggle_fullscreen()

    def show(self):
        self.window.makeKeyAndOrderFront_(self.window)

        if not BrowserView.app.isRunning():
            # Add the default Cocoa application menu
            self._add_app_menu()
            self._add_view_menu()

            BrowserView.app.activateIgnoringOtherApps_(Foundation.YES)
            BrowserView.app.run()
        else:
            self.webview_ready.set()

    def destroy(self):
        PyObjCTools.AppHelper.callAfter(self.window.close)

    def set_title(self, title):
        def _set_title():
            self.window.setTitle_(title)

        PyObjCTools.AppHelper.callAfter(_set_title)

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
            self._current_url_semaphore.release()

        PyObjCTools.AppHelper.callAfter(get)

        self._current_url_semaphore.acquire()
        return self._current_url

    def load_url(self, url):
        def load(url):
            page_url = Foundation.NSURL.URLWithString_(url)
            req = Foundation.NSURLRequest.requestWithURL_(page_url)
            self.webkit.mainFrame().loadRequest_(req)

        self.loaded.clear()
        self.url = url
        PyObjCTools.AppHelper.callAfter(load, url)

    def load_html(self, content, base_uri):
        def load(content, url):
            url = Foundation.NSURL.URLWithString_(url)
            self.webkit.mainFrame().loadHTMLString_baseURL_(content, url)

        self.loaded.clear()
        PyObjCTools.AppHelper.callAfter(load, content, base_uri)

    def evaluate_js(self, script):
        def evaluate(script):
            result = self.webkit.windowScriptObject().evaluateWebScript_(script)

            if result is WebKit.WebUndefined.undefined():
                JSResult.result = None
            else:
                try:
                    JSResult.result = result.__reduce__()[1][0]
                except TypeError:
                    JSResult.result = result

            JSResult.result_semaphore.release()

        class JSResult:
            result = None
            result_semaphore = Semaphore(0)

        self.loaded.wait()
        PyObjCTools.AppHelper.callAfter(evaluate, script)

        JSResult.result_semaphore.acquire()
        return JSResult.result

    def _set_js_api(self):
        script = _parse_api_js(self.js_bridge.api)
        self.webkit.windowScriptObject().evaluateWebScript_(script)

        pwv_obj = self.webkit.windowScriptObject().valueForKey_('pywebview')
        pwv_obj.setValue_forKey_(self.js_bridge, '_bridge')

    def create_file_dialog(self, dialog_type, directory, allow_multiple, save_filename, file_filter, main_thread=False):
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

                # Set allowed file extensions
                if file_filter:
                    open_dlg.setAllowedFileTypes_(file_filter[0][1])

                    # Add a menu to choose between multiple file filters
                    if len(file_filter) > 1:
                        filter_chooser = BrowserView.FileFilterChooser.alloc().initWithFilter_(file_filter)
                        open_dlg.setAccessoryView_(filter_chooser)
                        open_dlg.setAccessoryViewDisclosed_(True)

                if directory:  # set initial directory
                    open_dlg.setDirectoryURL_(Foundation.NSURL.fileURLWithPath_(directory))

                if open_dlg.runModal() == AppKit.NSFileHandlingPanelOKButton:
                    files = open_dlg.filenames()
                    self._file_name = tuple(files)
                else:
                    self._file_name = None

            if not main_thread:
                self._file_name_semaphore.release()

        if main_thread:
            create_dialog(dialog_type, allow_multiple, save_filename)
        else:
            PyObjCTools.AppHelper.callAfter(create_dialog, dialog_type, allow_multiple, save_filename)
            self._file_name_semaphore.acquire()

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

    @staticmethod
    def nscolor_from_hex(hex_string):
        """
        Convert given hex color to NSColor.

        :hex_string: Hex code of the color as #RGB or #RRGGBB
        """

        hex_string = hex_string[1:]     # Remove leading hash
        if len(hex_string) == 3:
            hex_string = ''.join([c*2 for c in hex_string]) # 3-digit to 6-digit

        hex_int = int(hex_string, 16)
        rgb = (
            (hex_int >> 16) & 0xff,     # Red byte
            (hex_int >> 8) & 0xff,      # Blue byte
            (hex_int) & 0xff            # Green byte
        )
        rgb = [i / 255.0 for i in rgb]      # Normalize to range(0.0, 1.0)

        return AppKit.NSColor.colorWithSRGBRed_green_blue_alpha_(rgb[0], rgb[1], rgb[2], 1.0)

    @staticmethod
    def get_instance(attr, value):
        """
        Return a BrowserView instance by the :value of its given :attribute,
        and None if no match is found.
        """
        for i in list(BrowserView.instances.values()):
            try:
                if getattr(i, attr) == value:
                    return i
            except AttributeError:
                break

        return None

    @staticmethod
    def display_confirmation_dialog(first_button, second_button, message):
        AppKit.NSApplication.sharedApplication()
        AppKit.NSRunningApplication.currentApplication().activateWithOptions_(AppKit.NSApplicationActivateIgnoringOtherApps)
        alert = AppKit.NSAlert.alloc().init()
        alert.addButtonWithTitle_(first_button)
        alert.addButtonWithTitle_(second_button)
        alert.setMessageText_(message)
        alert.setAlertStyle_(AppKit.NSWarningAlertStyle)

        if alert.runModal() == AppKit.NSAlertFirstButtonReturn:
            return True
        else:
            return False

    @staticmethod
    def _set_debugging():
        command = ['defaults', 'write', 'org.python.python', 'WebKitDeveloperExtras', '-bool', 'true']
        if sys.version < '3':
            subprocess.call(command)
        else:
            subprocess.run(command)


def create_window(uid, title, url, width, height, resizable, fullscreen, min_size,
                  confirm_quit, background_color, debug, js_api, webview_ready):
    def create():
        browser = BrowserView(uid, title, url, width, height, resizable, fullscreen, min_size,
                              confirm_quit, background_color, debug, js_api, webview_ready)
        browser.show()

    if uid == 'master':
        create()
    else:
        PyObjCTools.AppHelper.callAfter(create)


def set_title(title, uid):
    BrowserView.instances[uid].set_title(title)


def create_file_dialog(dialog_type, directory, allow_multiple, save_filename, file_types):
    file_filter = []

    # Parse file_types to obtain allowed file extensions
    for s in file_types:
        description, extensions = _parse_file_type(s)
        file_extensions = [i.lstrip('*.') for i in extensions.split(';') if i != '*.*']
        file_filter.append([description, file_extensions or None])

    i = list(BrowserView.instances.values())[0]     # arbitary instance
    return i.create_file_dialog(dialog_type, directory, allow_multiple, save_filename, file_filter)


def load_url(url, uid):
    BrowserView.instances[uid].load_url(url)


def load_html(content, base_uri, uid):
    BrowserView.instances[uid].load_html(content, base_uri)


def destroy_window(uid):
    BrowserView.instances[uid].destroy()


def toggle_fullscreen(uid):
    BrowserView.instances[uid].toggle_fullscreen()


def get_current_url(uid):
    return BrowserView.instances[uid].get_current_url()


def evaluate_js(script, uid):
    return BrowserView.instances[uid].evaluate_js(script)
