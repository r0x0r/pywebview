"""
Cocoa window cannot be destroyed programmatically, until it finishes processing a NSEvent
So we need to simulate a mouse movement in order to generate an event.
"""

from Quartz.CoreGraphics import CGEventCreateMouseEvent
from Quartz.CoreGraphics import CGEventCreate
from Quartz.CoreGraphics import CGEventGetLocation
from Quartz.CoreGraphics import CFRelease
from Quartz.CoreGraphics import CGEventPost
from Quartz.CoreGraphics import kCGEventMouseMoved
from Quartz.CoreGraphics import kCGEventLeftMouseDown
from Quartz.CoreGraphics import kCGEventLeftMouseUp
from Quartz.CoreGraphics import kCGMouseButtonLeft
from Quartz.CoreGraphics import kCGHIDEventTap


def mousePos():
    event = CGEventCreate(None)
    pointer = CGEventGetLocation(event)
    #CFRelease(event)
    return pointer.x, pointer.y


def mouseEvent(type, posx, posy):
    theEvent = CGEventCreateMouseEvent(None, type, (posx, posy), kCGMouseButtonLeft)
    CGEventPost(kCGHIDEventTap, theEvent)


def mouseMove(posx, posy):
    mousePos()
    mouseEvent(kCGEventMouseMoved, posx, posy)


def mouseMoveRelative(dx, dy):
    posx, posy = mousePos()
    mouseMove(posx + dx, posy + dy)


def mouseclick(posx, posy):
    mouseEvent(kCGEventLeftMouseDown, posx, posy)
    mouseEvent(kCGEventLeftMouseUp, posx, posy)


if __name__ == '__main__':
    mouseMoveRelative(100, 100)