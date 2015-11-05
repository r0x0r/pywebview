#!/usr/bin/env python
"""Copyright (C) 2013 COLDWELL AG

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

from AppKit import NSURL, NSURLRequest, NSMakeSize
import WebKit

# this saves import time
NSTitledWindowMask = 1
NSClosableWindowMask = 2
NSResizableWindowMask = 8
NSBackingStoreBuffered = 2
NSScreenSaverWindowLevel = 1000
NSWindowCollectionBehaviorCanJoinAllSpaces = 1

class Window(object):
    def __init__(self, win, title, frame, deleg):
        win.initWithContentRect_styleMask_backing_defer_(
            frame,
            NSTitledWindowMask | NSClosableWindowMask | NSResizableWindowMask,
            NSBackingStoreBuffered,
            False)
        win.setAcceptsMouseMovedEvents_(True)
        win.setReleasedWhenClosed_(False)
        self.window = win
        win.setLevel_(NSScreenSaverWindowLevel+1)
        win.setCollectionBehavior_(NSWindowCollectionBehaviorCanJoinAllSpaces)
        if deleg:
            win.setDelegate_(deleg)
            self.callbacks = deleg
        else:
            self.callbacks = None
        self._webkit = None
        self.inputs = dict()
        
    @classmethod
    def web(cls, win, title, frame, deleg):
        self = cls(win, title, frame, deleg)
        w = self._web(frame[0], frame[1])
        w.setUIDelegate_(deleg)
        self.window.setContentView_(w)
        self._webkit = w
        return self
        
    def _web(self, pos, size):
        return WebKit.WebView.alloc().initWithFrame_((pos, size))

    def goto(self, url, show=True):
        if self._webkit is None:
            raise RuntimeError("needs to be a web window")
        url = NSURL.URLWithString_(url).retain()
        request = NSURLRequest.requestWithURL_(url)
        self._webkit.mainFrame().loadRequest_(request)
        self.show()
    
    def sethtml(self, html, url, show=True):
        if self._webkit is None:
            raise RuntimeError("needs to be the web window")
        url = NSURL.URLWithString_(url).retain()
        if isinstance(html, str):
            html = html.decode("utf-8")
        self._webkit.mainFrame().loadHTMLString_baseURL_(html, url)
        self.show()
        
    def javascript(self, s):
        return self._webkit.stringByEvaluatingJavaScriptFromString_(s)
        
    def show(self):
        self.window.display()
        self.window.orderFrontRegardless()
        
    def hide(self):
        self.sethtml("", "about:blank")
        self.window.close()
        
    def size(self, width, height):
        size = NSMakeSize(float(width), float(height))
        self.window.setContentSize_(size)
