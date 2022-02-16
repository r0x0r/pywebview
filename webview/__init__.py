#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
pywebview is a lightweight cross-platform wrapper around a webview component that allows to display HTML content in its
own dedicated window. Works on Windows, OS X and Linux and compatible with Python 2 and 3.

(C) 2014-2019 Roman Sirokov and contributors
Licensed under BSD license

http://github.com/r0x0r/pywebview/
"""


import logging
import sys
import os
import re
import threading
from uuid import uuid4
from proxy_tools import module_property

from webview.event import Event
from webview.guilib import initialize
from webview.util import _token, base_uri, parse_file_type, escape_string, make_unicode, escape_line_breaks, WebViewException
from webview.window import Window
from .localization import original_localization
from .wsgi import Routing, StaticFiles, StaticResources


__all__ = (
    # Stuff that's here
    'start', 'create_window', 'token', 'screens'
    # From wsgi
    'Routing', 'StaticFiles', 'StaticResources',
    # From event
    'Event',
    # from util
    '_token', 'base_uri', 'parse_file_type', 'escape_string', 'make_unicode',
    'escape_line_breaks', 'WebViewException',
    # from window
    'Window',
)

logger = logging.getLogger('pywebview')
handler = logging.StreamHandler()
formatter = logging.Formatter('[pywebview] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

log_level = logging.DEBUG if os.environ.get('PYWEBVIEW_LOG') == 'debug' else logging.INFO
logger.setLevel(log_level)

OPEN_DIALOG = 10
FOLDER_DIALOG = 20
SAVE_DIALOG = 30

DRAG_REGION_SELECTOR = '.pywebview-drag-region'

guilib = None
_debug = {
  'mode': False
}
_user_agent = None
_multiprocessing = False
_http_server = False

token = _token
windows = []

def start(func=None, args=None, localization={}, gui=None, debug=False, http_server=False, user_agent=None):
    """
    Start a GUI loop and display previously created windows. This function must
    be called from a main thread.

    :param func: Function to invoke upon starting the GUI loop.
    :param args: Function arguments. Can be either a single value or a tuple of
        values.
    :param localization: A dictionary with localized strings. Default strings
        and their keys are defined in localization.py.
    :param gui: Force a specific GUI. Allowed values are ``cef``, ``qt``, or
        ``gtk`` depending on a platform.
    :param debug: Enable debug mode. Default is False.
    :param http_server: Enable built-in HTTP server. If enabled, local files
        will be served using a local HTTP server on a random port. For each
        window, a separate HTTP server is spawned. This option is ignored for
        non-local URLs.
    :param user_agent: Change user agent string. Not supported in EdgeHTML.
    """
    global guilib, _debug, _multiprocessing, _http_server, _user_agent

    def _create_children(other_windows):
        if not windows[0].events.shown.wait(10):
            raise WebViewException('Main window failed to load')

        for window in other_windows:
            guilib.create_window(window)

    _debug['mode'] = debug

    if debug:
        logger.setLevel(logging.DEBUG)

    _user_agent = user_agent
    #_multiprocessing = multiprocessing
    multiprocessing = False # TODO
    _http_server = http_server

    if multiprocessing:
        from multiprocessing import Process as Thread
    else:
        from threading import Thread

    original_localization.update(localization)

    if threading.current_thread().name != 'MainThread':
        raise WebViewException('This function must be run from a main thread.')

    if len(windows) == 0:
        raise WebViewException('You must create a window first before calling this function.')

    guilib = initialize(gui)

    for window in windows:
        window._initialize(guilib, multiprocessing, http_server)

    if len(windows) > 1:
        t = Thread(target=_create_children, args=(windows[1:],))
        t.start()

    if func:
        if args is not None:
            if not hasattr(args, '__iter__'):
                args = (args,)
            t = Thread(target=func, args=args)
        else:
            t = Thread(target=func)
        t.start()

    guilib.create_window(windows[0])


def create_window(title, url=None, html=None, js_api=None, width=800, height=600, x=None, y=None,
                  resizable=True, fullscreen=False, min_size=(200, 100), hidden=False,
                  frameless=False, easy_drag=True,
                  minimized=False, on_top=False, confirm_close=False, background_color='#FFFFFF',
                  transparent=False, text_select=False, localization=None):
    """
    Create a web view window using a native GUI. The execution blocks after this function is invoked, so other
    program logic must be executed in a separate thread.
    :param title: Window title
    :param url: URL to load
    :param width: window width. Default is 800px
    :param height:window height. Default is 600px
    :param resizable True if window can be resized, False otherwise. Default is True
    :param fullscreen: True if start in fullscreen mode. Default is False
    :param min_size: a (width, height) tuple that specifies a minimum window size. Default is 200x100
    :param hidden: Whether the window should be hidden.
    :param frameless: Whether the window should have a frame.
    :param easy_drag: Easy window drag mode when window is frameless.
    :param minimized: Display window minimized
    :param on_top: Keep window above other windows (required OS: Windows)
    :param confirm_close: Display a window close confirmation dialog. Default is False
    :param background_color: Background color as a hex string that is displayed before the content of webview is loaded. Default is white.
    :param text_select: Allow text selection on page. Default is False.
    :param transparent: Don't draw window background.
    :return: window object.
    """

    valid_color = r'^#(?:[0-9a-fA-F]{3}){1,2}$'
    if not re.match(valid_color, background_color):
        raise ValueError('{0} is not a valid hex triplet color'.format(background_color))

    uid = 'master' if len(windows) == 0 else 'child_' + uuid4().hex[:8]

    window = Window(uid, make_unicode(title), url, html,
                    width, height, x, y, resizable, fullscreen, min_size, hidden,
                    frameless, easy_drag, minimized, on_top, confirm_close, background_color,
                    js_api, text_select, transparent, localization)

    windows.append(window)

    if threading.current_thread().name != 'MainThread' and guilib:
        window._initialize(guilib, _multiprocessing, _http_server)
        guilib.create_window(window)

    return window


@module_property
def screens():
    guilib = initialize()
    screens = guilib.get_screens()
    return screens
