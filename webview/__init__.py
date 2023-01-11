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
import os
import re
import threading
from uuid import uuid4
from proxy_tools import module_property

import webview.http as http

from webview.guilib import initialize
from webview.util import _token, base_uri, parse_file_type, is_app, is_local_url, escape_string, escape_line_breaks, WebViewException
from webview.window import Window
from .localization import original_localization


__all__ = (
    # Stuff that's here
    'start', 'create_window', 'token', 'screens'
    # From event
    'Event',
    # from util
    '_token', 'base_uri', 'parse_file_type', 'escape_string',
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
DEFAULT_HTTP_PORT = 42001

guilib = None
_debug = {
  'mode': False
}
_user_agent = None
_http_server = False
_private_mode = True
_storage_path = None

token = _token
windows = []
menus = []

def start(func=None, args=None, localization={}, gui=None, debug=False, http_server=False,
          http_port=None, user_agent=None, private_mode=True, storage_path=None, menu=[], server=http.BottleServer, server_args={}):
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
    :param private_mode: Enable private mode. In private mode, cookies and local storage are not preserved.
           Default is True.
    :param storage_path: Custom location for cookies and other website data
    :param menu: List of menus to be included in the app menu
    :param server: Server class. Defaults to BottleServer
    :param server_args: Dictionary of arguments to pass through to the server instantiation
    """
    global guilib, _debug, _http_server, _user_agent, _private_mode, _storage_path

    def _create_children(other_windows):
        if not windows[0].events.shown.wait(10):
            raise WebViewException('Main window failed to load')

        for window in other_windows:
            guilib.create_window(window)

    _debug['mode'] = debug

    if debug:
        logger.setLevel(logging.DEBUG)

    _user_agent = user_agent
    _http_server = http_server
    _private_mode = private_mode
    _storage_path = storage_path

    if _storage_path and _private_mode and not os.path.exists(_storage_path):
        os.makedirs(_storage_path)

    original_localization.update(localization)

    if threading.current_thread().name != 'MainThread':
        raise WebViewException('This function must be run from a main thread.')

    if len(windows) == 0:
        raise WebViewException('You must create a window first before calling this function.')

    guilib = initialize(gui)

    urls = [w.original_url for w in windows]
    has_local_urls = not not [
        w.original_url
        for w in windows
        if is_app(w.original_url) or is_local_url(w.original_url)
    ]

    # start the global server if it's not running and we need it
    if (http.global_server is None) and \
        (http_server or has_local_urls or (guilib.renderer == 'gtkwebkit2')):
            if not _private_mode and not http_port:
                http_port = DEFAULT_HTTP_PORT
            prefix, common_path, server = http.start_global_server(http_port=http_port, urls=urls, server=server, **server_args)
    
    for window in windows:
        window._initialize(guilib)

    if len(windows) > 1:
        t = threading.Thread(target=_create_children, args=(windows[1:],))
        t.start()

    if func:
        if args is not None:
            if not hasattr(args, '__iter__'):
                args = (args,)
            t = threading.Thread(target=func, args=args)
        else:
            t = threading.Thread(target=func)
        t.start()

    guilib.set_app_menu(menu)
    guilib.create_window(windows[0])


def create_window(title, url=None, html=None, js_api=None, width=800, height=600, x=None, y=None,
                  resizable=True, fullscreen=False, min_size=(200, 100), hidden=False,
                  frameless=False, easy_drag=True,
                  minimized=False, on_top=False, confirm_close=False, background_color='#FFFFFF',
                  transparent=False, text_select=False, zoomable=False, draggable=False, localization=None,
                  server=http.BottleServer, server_args={}):
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
    :param server: Server class. Defaults to BottleServer
    :param server_args: Dictionary of arguments to pass through to the server instantiation
    :return: window object.
    """

    valid_color = r'^#(?:[0-9a-fA-F]{3}){1,2}$'
    if not re.match(valid_color, background_color):
        raise ValueError('{0} is not a valid hex triplet color'.format(background_color))

    uid = 'master' if len(windows) == 0 else 'child_' + uuid4().hex[:8]

    window = Window(uid, title, url, html,
                    width, height, x, y, resizable, fullscreen, min_size, hidden,
                    frameless, easy_drag, minimized, on_top, confirm_close, background_color,
                    js_api, text_select, transparent, zoomable, draggable, localization, 
                    server=server, server_args=server_args)

    windows.append(window)

    # This immediately creates the window only if `start` has already been called
    if threading.current_thread().name != 'MainThread' and guilib:
        if is_app(url) or is_local_url(url) and not http.running:
            url_prefix, common_path, server = http.start_server([url], server=server, **server_args)
        else:
            url_prefix, common_path, server = None, None, None

        window._initialize(gui = guilib, server = server)
        guilib.create_window(window)

    return window

def active_window():
    """
    Get the active window

    :return: window object or None
    """
    if guilib:
        return guilib.get_active_window()
    return None

@module_property
def screens():
    guilib = initialize()
    screens = guilib.get_screens()
    return screens

