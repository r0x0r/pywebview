"""
Cocoa window cannot be destroyed programmatically, until it finishes processing a NSEvent
So we need to simulate a mouse movement in order to generate an event.
"""

from Quartz.CoreGraphics import CGEventCreateMouseEvent
from Quartz.CoreGraphics import CGEventPost
from Quartz.CoreGraphics import kCGEventMouseMoved
from Quartz.CoreGraphics import kCGEventLeftMouseDown
from Quartz.CoreGraphics import kCGEventLeftMouseDown
from Quartz.CoreGraphics import kCGEventLeftMouseUp
from Quartz.CoreGraphics import kCGMouseButtonLeft
from Quartz.CoreGraphics import kCGHIDEventTap

def mouseEvent(type, posx, posy):
        theEvent = CGEventCreateMouseEvent(
                    None,
                    type,
                    (posx,posy),
                    kCGMouseButtonLeft)
        CGEventPost(kCGHIDEventTap, theEvent)


def mousemove(posx, posy):
        mouseEvent(kCGEventMouseMoved, posx,posy);


def mouseclick(posx, posy):
        # uncomment this line if you want to force the mouse
        # to MOVE to the click location first (I found it was not necessary).
        #mouseEvent(kCGEventMouseMoved, posx,posy);
        mouseEvent(kCGEventLeftMouseDown, posx,posy);
        mouseEvent(kCGEventLeftMouseUp, posx,posy);
