#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
pywebview is a lightweight cross-platform wrapper around a webview component that allows to display HTML content in its
own dedicated window. Works on Windows, OS X and Linux and compatible with Python 2 and 3.

(C) 2014-2019 Roman Sirokov and contributors
Licensed under BSD license

http://github.com/r0x0r/pywebview/
"""


import json
import logging
import os
import platform
import re
import sys
from threading import Event, Thread, current_thread
from uuid import uuid4
from functools import wraps
from copy import deepcopy

from webview.util import base_uri, parse_file_type, escape_string, transform_url, make_unicode, escape_line_breaks, inject_base_uri
from .js import css
from .localization import localization as original_localization


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


class WebViewException(Exception):
    pass


_initialized = False

def _initialize_imports(forced_gui):
    def import_gtk():
        global guilib

        try:
            import webview.gtk as guilib
            logger.debug('Using GTK')

            return True
        except (ImportError, ValueError) as e:
            logger.exception('GTK cannot be loaded')

            return False

    def import_qt():
        global guilib

        try:
            import webview.qt as guilib

            return True
        except ImportError as e:
            logger.exception('QT cannot be loaded')
            return False

    def import_cocoa():
        global guilib

        try:
            import webview.cocoa as guilib

            return True
        except ImportError:
            logger.exception('PyObjC cannot be loaded')

            return False

    def import_winforms():
        global guilib

        try:
            import webview.winforms as guilib
            logger.debug('Using .NET')

            return True
        except ImportError as e:
            logger.exception('pythonnet cannot be loaded')
            return False

    def try_import(guis):
        while guis:
            import_func = guis.pop(0)

            if import_func():
                return True

        return False

    global _initialized

    if not forced_gui:
        forced_gui = 'qt' if 'KDE_FULL_SESSION' in os.environ else None
        forced_gui = os.environ['PYWEBVIEW_GUI'].lower() \
            if 'PYWEBVIEW_GUI' in os.environ and os.environ['PYWEBVIEW_GUI'].lower() in ['qt', 'gtk', 'cef'] \
            else None

    if platform.system() == 'Darwin':
        if forced_gui == 'qt':
            guis = [import_qt, import_cocoa]
        else:
            guis = [import_cocoa, import_qt]

        if not try_import(guis):
            raise WebViewException('You must have either PyObjC (for Cocoa support) or Qt with Python bindings installed in order to use pywebview.')

    elif platform.system() == 'Linux' or platform.system() == 'OpenBSD':
        if forced_gui== 'gtk' or forced_gui != 'qt':
            guis = [import_gtk, import_qt]
        else:
            guis = [import_qt, import_gtk]

        if not try_import(guis):
            raise WebViewException('You must have either QT or GTK with Python extensions installed in order to use pywebview.')

    elif platform.system() == 'Windows':
        guis = [import_winforms]

        if not try_import(guis):
            raise WebViewException('You must have either pythonnet or pywin32 installed in order to use pywebview.')
    else:
        raise WebViewException('Unsupported platform. Only Windows, Linux, OS X, OpenBSD are supported.')

    _initialized = True


def _api_call(function):
    """
    Decorator to call a pywebview API, checking for _webview_ready and raisings
    appropriate Exceptions on failure.
    """
    @wraps(function)
    def wrapper(*args, **kwargs):
        try:
            if not args[0].shown_event.wait(15):
                raise WebViewException('Main window failed to start')
            return function(*args, **kwargs)
        except NameError:
            raise WebViewException('Create a web view window first, before invoking this function')

    return wrapper


windows = []


class Window:
    def __init__(self, uid, title, url, width, height, resizable, fullscreen,
                 min_size, confirm_quit, background_color, js_api, text_select, frameless):
        self.uid = uid
        self.title = make_unicode(title)
        self.url = transform_url(url)
        self.width = width
        self.height = height
        self.resizable = resizable
        self.fullscreen = fullscreen
        self.min_size = min_size
        self.confirm_quit = confirm_quit
        self.background_color = background_color
        self.js_api = js_api
        self.text_select = text_select
        self.frameless = frameless

        self.shown_event = Event()
        self.loaded_event = Event()

        self.loaded = []
        self.shown = []

    @_api_call
    def load_url(self, url):
        """
        Load a new URL into a previously created WebView window. This function must be invoked after WebView windows is
        created with create_window(). Otherwise an exception is thrown.
        :param url: url to load
        :param uid: uid of the target instance
        """
        guilib.load_url(url, self.uid)

    @_api_call
    def load_html(self, content, base_uri=base_uri()):
        """
        Load a new content into a previously created WebView window. This function must be invoked after WebView windows is
        created with create_window(). Otherwise an exception is thrown.
        :param content: Content to load.
        :param base_uri: Base URI for resolving links. Default is the directory of the application entry point.
        :param uid: uid of the target instance
        """
        content = make_unicode(content)
        guilib.load_html(content, base_uri, self.uid)

    @_api_call
    def load_css(self, stylesheet):
        code = css.src % stylesheet.replace('\n', '').replace('\r', '').replace('"', "'")
        guilib.evaluate_js(code, self.uid)

    @_api_call
    def set_title(self, title):
        """
        Sets a new title of the window
        """
        guilib.set_title(title, self.uid)

    @_api_call
    def get_current_url(self):
        """
        Get the URL currently loaded in the target webview
        """
        return guilib.get_current_url(self.uid)

    @_api_call
    def destroy_window(self):
        """
        Destroy a web view window
        """
        guilib.destroy_window(self.uid)

    @_api_call
    def toggle_fullscreen(self):
        """
        Toggle fullscreen mode
        """
        guilib.toggle_fullscreen(self.uid)

    @_api_call
    def set_window_size(self, width, height):
        """
        Set Window Size
        :param width: desired width of target window
        :param height: desired height of target window
        """
        guilib.set_window_size(width, height)

    @_api_call
    def evaluate_js(self, script):
        """
        Evaluate given JavaScript code and return the result
        :param script: The JavaScript code to be evaluated
        :return: Return value of the evaluated code
        """
        escaped_script = 'JSON.stringify(eval("{0}"))'.format(escape_string(script))
        return guilib.evaluate_js(escaped_script, self.uid)

    @_api_call
    def create_file_dialog(self, dialog_type=OPEN_DIALOG, directory='', allow_multiple=False, save_filename='', file_types=()):
        """
        Create a file dialog
        :param dialog_type: Dialog type: open file (OPEN_DIALOG), save file (SAVE_DIALOG), open folder (OPEN_FOLDER). Default
                            is open file.
        :param directory: Initial directory
        :param allow_multiple: Allow multiple selection. Default is false.
        :param save_filename: Default filename for save file dialog.
        :param file_types: Allowed file types in open file dialog. Should be a tuple of strings in the format:
            filetypes = ('Description (*.extension[;*.extension[;...]])', ...)
        :return: A tuple of selected files, None if cancelled.
        """
        if type(file_types) != tuple and type(file_types) != list:
            raise TypeError('file_types must be a tuple of strings')
        for f in file_types:
            parse_file_type(f)

        if not os.path.exists(directory):
            directory = ''

        return guilib.create_file_dialog(dialog_type, directory, allow_multiple, save_filename, file_types, self.uid)


def start(func=None, args=None, localization={}, multiprocessing=False, gui=None, debug=False):
    def _create_children():
        if not windows[0].shown_event.wait(10):
            raise WebViewException('Main window failed to load')

        for window in windows[1:]:
            guilib.create_window(window, debug)

    if multiprocessing:
        from multiprocessing import Process as Thread
    else:
        from threading import Thread

    original_localization.update(localization)

    if current_thread().name != 'MainThread':
        raise WebViewException('This function must be run from a main thread.')

    if len(windows) == 0:
        raise WebViewException('You must create a window first before calling this function.')

    _initialize_imports(gui)

    if len(windows) > 1:
        t = Thread(target=_create_children)
        t.start()

    if func:
        if args is not None:
            if not hasattr(args, '__iter__'):
                args = (args,)
            t = Thread(target=func, args=args)
        else:
            t = Thread(target=func)
        t.start()

    guilib.create_window(windows[0], debug)


def create_window(title, url=None, js_api=None, width=800, height=600,
                  resizable=True, fullscreen=False, min_size=(200, 100), confirm_quit=False,
                  background_color='#FFFFFF', text_select=False, frameless=False):
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
    :param confirm_quit: Display a quit confirmation dialog. Default is False
    :param background_color: Background color as a hex string that is displayed before the content of webview is loaded. Default is white.
    :param text_select: Allow text selection on page. Default is False.
    :param frameless: Whether the window should have a frame.
    :return: The uid of the created window.
    """

    valid_color = r'^#(?:[0-9a-fA-F]{3}){1,2}$'
    if not re.match(valid_color, background_color):
        raise ValueError('{0} is not a valid hex triplet color'.format(background_color))

    uid = 'master' if current_thread().name == 'MainThread' else 'child_' + uuid4().hex[:8]

    window = Window(uid, make_unicode(title), transform_url(url),
                    width, height, resizable, fullscreen, min_size, confirm_quit,
                    background_color, js_api, text_select, frameless)
    windows.append(window)

    if current_thread().name != 'MainThread' and _initialized:
        guilib.create_window(window, False) # TODO

    return window
    """
    _webview_ready.clear()  # Make API calls wait while the new window is created
    gui.create_window(uid, make_unicode(title), transform_url(url),
                      width, height, resizable, fullscreen, min_size, confirm_quit,
                      background_color, js_api, text_select, frameless, _webview_ready)

    if uid == 'master':
        _webview_ready.clear()
    else:
        return uid
    """



def window_exists(uid='master'):
    """
    Check whether a webview with the given UID is up and running
    :param uid: uid of the target instance
    :return: True if the window exists, False otherwise
    """
    try:
        get_current_url(uid)
        return True
    except:
        return False


def _js_bridge_call(window, func_name, param):
    def _call():
        result = json.dumps(func(func_params))
        code = 'window.pywebview._returnValues["{0}"] = {{ isSet: true, value: {1}}}'.format(func_name, escape_line_breaks(result))
        window.evaluate_js(code)

    func = getattr(window.js_api, func_name, None)

    if func is not None:
        try:
            func_params = param if not param else json.loads(param)
            t = Thread(target=_call)
            t.start()
        except Exception:
            logger.exception('Error occurred while evaluating function {0}'.format(func_name))
    else:
        logger.error('Function {}() does not exist'.format(func_name))
