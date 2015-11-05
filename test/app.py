#!/usr/bin/env python
# encoding: utf-8
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

import sys
import signal
import atexit
import os


#import gevent
from window import Window

from AppKit import NSMenuItem, NSMenu, NSStatusBar, NSImage, NSSize, NSApplication, NSWindow, NSObject, NSTimer, NSDate, NSRunLoop

from PyObjCTools import AppHelper


NSDefaultRunLoopMode = u'kCFRunLoopDefaultMode'

#timerevent = Event()
class Delegate(NSObject):
    def restart_(self, noti):
        pass
        #gevent.spawn(patch.restart_app)

    """
    def open_(self, notification):
        common.open_browser()
        
    def login_(self, noti):
        common.relogin()
        
    def logout_(self, notification):
        common.relogin()
    
    def test_(self, noti):
        common.relogin()
        
    def register_(self, noti):
        common.register()
        
    def quit_(self, notification):
        exit(0)
    """
        
    #def gevent_(self, notification):
    #    gevent.sleep(0.1)
        
def mac_sigint(*args):
    exit(0)

def draw_browser(wind, deleg):
    frame = ((0.0, 0.0), (400, 10))
    return Window.web(wind, "Browser", frame, deleg)

browserwindow = None

def build_menu(labels):
    menu = NSMenu.alloc().init()
    menu.setAutoenablesItems_(True)
    """
    for label in labels:
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            localize._X(label), label.lower().replace(" ", "").split(" ")[0]+":", "")
            
        iconpath = os.path.join(settings.menuiconfolder, label.lower() + ".icns")
        if os.path.exists(iconpath):
            img = NSImage.alloc().initByReferencingFile_(iconpath)
            img.setSize_(NSSize(16, 16))
            item.setImage_(img)
        menu.addItem_(item)
    """
    return menu

NSVariableStatusItemLength = -1
def start_taskbar():
    t = NSStatusBar.systemStatusBar()
    icon = t.statusItemWithLength_(NSVariableStatusItemLength)
    icon.setHighlightMode_(1)

    def update_tooltip():
        pass
        #text = common.generate_tooltip_text()
        #icon.setToolTip_(text)
        #gevent.spawn_later(5, update_tooltip)
        #gevent.spawn_later(5, update_tooltip)
        
    def set_image(path):
        taskbarimg = NSImage.alloc().initByReferencingFile_(path)
        taskbarimg.setSize_(NSSize(18, 18))
        icon.setImage_(taskbarimg)
        
    # taskbar icon switching
    #@event.register("api:connected")
    #def set_active(*_):
    #    set_image(settings.taskbaricon)

    #@event.register("api:disconnected")
    #@event.register("api:connection_error")
    #def set_inactive(*_):
    #    set_image(settings.taskbaricon_inactive)
    
    #set_image(settings.taskbaricon_inactive)
    icon.setEnabled_(True)
    
    #@event.register('login:changed')
    def login_changed(*_):
        opts = ["Open"]
        """
        if login.is_guest() or not login.has_login():
            opts.append("Login")
            opts.append("Register")
        elif login.has_login():
            opts.append("Logout")
        else:
            opts.append("Register")
        """
        opts.append("Quit")
        icon.setMenu_(build_menu(opts))
    
    login_changed()

def gevent_timer(deleg):
    timer = NSTimer.alloc().initWithFireDate_interval_target_selector_userInfo_repeats_(
        NSDate.date(), 0.1, deleg, 'gevent:', None, True)
    NSRunLoop.currentRunLoop().addTimer_forMode_(timer, NSDefaultRunLoopMode)
    timer.fire()
    print "started gevent timer"

_exited = False
def exit(code=0):
    global _exited
    if _exited:
        return
    AppHelper.stopEventLoop()
    #from .... import loader
    #loader.terminate()
    _exited = True
    
def init():
    print "init ui cocoa"
    global browserwindow
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(1)
    start_taskbar()
    app.finishLaunching()
    _browserwindow = NSWindow.alloc()
    #icon = NSImage.alloc().initByReferencingFile_(settings.mainicon)
    #app.setApplicationIconImage_(icon)
    
    deleg = Delegate.alloc()
    deleg.init()
    app.setDelegate_(deleg)
    
    signal.signal(signal.SIGINT, mac_sigint)
    
    from .input import BrowserDelegate
    bd = BrowserDelegate.alloc()
    bd.init()
    browserwindow = draw_browser(_browserwindow, bd)

    atexit.register(exit)
    #gevent_timer(deleg)
    #ui.module_initialized.set()
    sys.exit = exit
    AppHelper.runEventLoop()
