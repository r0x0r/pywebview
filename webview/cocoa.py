"""
(C) 2014 Roman Sirokov
Licensed under BSD license

http://github.com/r0x0r/pywebview/
"""
from Foundation import *
from AppKit import *
import WebKit




class BrowserView:
    instance = None
    app = NSApplication.sharedApplication()

    class AppDelegate(NSObject):
        def windowWillClose_(self, notification):
            BrowserView.app.terminate_(self)

    class WebKitHost(WebKit.WebView):

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
                        BrowserView.app.terminate_(self)

                    return handled

    def __init__(self, title, url, width, height, resizable, fullscreen):
        BrowserView.instance = self

        rect = NSMakeRect(100.0, 350.0, width, height)
        window_mask = NSTitledWindowMask | NSClosableWindowMask | NSMiniaturizableWindowMask

        if resizable:
            window_mask = window_mask | NSResizableWindowMask

        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(rect, window_mask,
                                                                                    NSBackingStoreBuffered, False)
        self.window.setTitle_(title)

        if fullscreen:
            NSWindowCollectionBehaviorFullScreenPrimary = 1 << 7
            newBehavior = self.window.collectionBehavior() | NSWindowCollectionBehaviorFullScreenPrimary
            self.window.setCollectionBehavior_(newBehavior)
            self.window.setCollectionBehavior_(NSWindowCollectionBehaviorFullScreenPrimary)
            self.window.toggleFullScreen_(None)

        self.webkit = BrowserView.WebKitHost.alloc()
        self.webkit.initWithFrame_(rect)
        self.load_url(url)

        self.window.setContentView_(self.webkit)
        self.myDelegate = BrowserView.AppDelegate.alloc().init()
        self.window.setDelegate_(self.myDelegate)

    def show(self):
        self.window.display()
        self.window.orderFrontRegardless()
        BrowserView.app.run()

    def load_url(self, url):
        self.url = url
        pageurl = Foundation.NSURL.URLWithString_(url)
        req = Foundation.NSURLRequest.requestWithURL_(pageurl)
        self.webkit.mainFrame().loadRequest_(req)






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




def load_url(url):
    if BrowserView.instance is not None:
        BrowserView.instance.load_url(url)
    else:
        raise Exception("Create a web view window first, before invoking this function")
