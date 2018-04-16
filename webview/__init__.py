#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
pywebview is a lightweight cross-platform wrapper around a webview component that allows to display HTML content in its
own dedicated window. Works on Windows, OS X and Linux and compatible with Python 2 and 3.

(C) 2014-2018 Roman Sirokov and contributors
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

from webview.util import base_uri, parse_file_type, escape_string, transform_url, make_unicode, escape_line_breaks, inject_base_uri
from .js import css
from .localization import localization

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

OPEN_DIALOG = 10
FOLDER_DIALOG = 20
SAVE_DIALOG = 30


class Config (dict):

    def __init__(self):
        self.use_qt = 'USE_QT' in os.environ
        self.use_win32 = 'USE_WIN32' in os.environ

    def __getitem__(self, key):
        return getattr(self, key.lower())

    def __setitem__(self, key, value):
        setattr(self, key.lower(), value)


config = Config()

_initialized = False
_webview_ready = Event()


def _initialize_imports():
    global _initialized, gui
    import_error = False

    if not _initialized:
        if platform.system() == 'Darwin':
            if not config.use_qt:
                try:
                    import webview.cocoa as gui
                except ImportError:
                    logger.exception('PyObjC cannot be loaded')
                    import_error = True

            if import_error or config.use_qt:
                try:
                    import webview.qt as gui
                    logger.debug('Using QT')
                except ImportError as e:
                    # Panic
                    logger.exception('QT cannot be loaded')
                    raise Exception('You must have either PyObjC (for Cocoa support) or Qt with Python bindings installed in order to use this library.')

        elif platform.system() == 'Linux' or platform.system() == 'OpenBSD':
            if not config.use_qt:
                try:
                    import webview.gtk as gui
                    logger.debug('Using GTK')
                except (ImportError, ValueError) as e:
                    logger.exception('GTK cannot be loaded')
                    import_error = True

            if import_error or config.use_qt:
                try:
                    # If GTK is not found, then try QT
                    import webview.qt as gui
                    logger.debug('Using QT')
                except ImportError as e:
                    # Panic
                    logger.exception('QT cannot be loaded')
                    raise Exception('You must have either QT or GTK with Python extensions installed in order to use this library.')

        elif platform.system() == 'Windows':
            #Try .NET first unless use_win32 flag is set
            if not config.use_win32:
                try:
                    import webview.winforms as gui
                    logger.debug('Using .NET')
                except ImportError as e:
                    logger.exception('pythonnet cannot be loaded')
                    import_error = True


            if import_error or config.use_win32:
                try:
                    # If .NET is not found, then try Win32
                    import webview.win32 as gui
                    logger.debug('Using Win32')
                except ImportError as e:
                    # Panic
                    logger.exception('PyWin32 cannot be loaded')
                    raise Exception('You must have either pythonnet or pywin32 installed in order to use this library.')
        else:
            raise Exception('Unsupported platform. Only Windows, Linux, OS X, OpenBSD are supported.')

        _initialized = True


def _api_call(function):
    """
    Decorator to call a pywebview API, checking for _webview_ready and raisings
    appropriate Exceptions on failure.
    """
    @wraps(function)
    def wrapper(*args, **kwargs):
        try:
            _webview_ready.wait(5)
            return function(*args, **kwargs)
        except NameError:
            raise Exception('Create a web view window first, before invoking this function')
        except KeyError:
            try:
                uid = kwargs['uid']
            except KeyError:
                # uid not passed as a keyword arg, assumes it to be last in the arg list
                uid = args[-1]
            raise Exception('Cannot call function: No webview exists with uid: {}'.format(uid))
    return wrapper


def create_window(title, url=None, js_api=None, width=800, height=600,
                  resizable=True, fullscreen=False, min_size=(200, 100), strings={}, confirm_quit=False,
                  background_color='#FFFFFF', text_select=False, debug=False):
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
    :param strings: a dictionary with localized strings
    :param confirm_quit: Display a quit confirmation dialog. Default is False
    :param background_color: Background color as a hex string that is displayed before the content of webview is loaded. Default is white.
    :param text_select: Allow text selection on page. Default is False.
    :return: The uid of the created window.
    """
    uid = 'child_' + uuid4().hex[:8]

    valid_color = r'^#(?:[0-9a-fA-F]{3}){1,2}$'
    if not re.match(valid_color, background_color):
        raise ValueError('{0} is not a valid hex triplet color'.format(background_color))

    if not _initialized:
        # Check if starting up from main thread; if not, wait; finally raise exception
        if current_thread().name != 'MainThread':
            if not _webview_ready.wait(5):
                raise Exception('Call create_window from the main thread first, and then from subthreads')
        else:
            _initialize_imports()
            localization.update(strings)
            uid = 'master'

    _webview_ready.clear()  # Make API calls wait while the new window is created
    gui.create_window(uid, make_unicode(title), transform_url(url),
                      width, height, resizable, fullscreen, min_size, confirm_quit,
                      background_color, debug, js_api, text_select, _webview_ready)

    return uid


@_api_call
def create_file_dialog(dialog_type=OPEN_DIALOG, directory='', allow_multiple=False, save_filename='', file_types=()):
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

    return gui.create_file_dialog(dialog_type, directory, allow_multiple, save_filename, file_types)


@_api_call
def load_url(url, uid='master'):
    """
    Load a new URL into a previously created WebView window. This function must be invoked after WebView windows is
    created with create_window(). Otherwise an exception is thrown.
    :param url: url to load
    :param uid: uid of the target instance
    """
    gui.load_url(url, uid)


@_api_call
def load_html(content, base_uri=base_uri(), uid='master'):
    """
    Load a new content into a previously created WebView window. This function must be invoked after WebView windows is
    created with create_window(). Otherwise an exception is thrown.
    :param content: Content to load.
    :param base_uri: Base URI for resolving links. Default is the directory of the application entry point.
    :param uid: uid of the target instance
    """
    content = make_unicode(content)
    gui.load_html(content, base_uri, uid)


@_api_call
def load_css(stylesheet, uid='master'):
    code = css.src % stylesheet.replace('\n', '').replace('\r', '').replace('"', "'")
    gui.evaluate_js(code)


@_api_call
def set_title(title, uid='master'):
    """
    Sets a new title of the window
    """
    gui.set_title(title, uid)


@_api_call
def get_current_url(uid='master'):
    """
    Get the URL currently loaded in the target webview
    :param uid: uid of the target instance
    """
    return gui.get_current_url(uid)


@_api_call
def destroy_window(uid='master'):
    """
    Destroy a web view window
    :param uid: uid of the target instance
    """
    gui.destroy_window(uid)


@_api_call
def toggle_fullscreen(uid='master'):
    """
    Toggle fullscreen mode
    :param uid: uid of the target instance
    """
    gui.toggle_fullscreen(uid)


@_api_call
def evaluate_js(script, uid='master'):
    """
    Evaluate given JavaScript code and return the result
    :param script: The JavaScript code to be evaluated
    :param uid: uid of the target instance
    :return: Return value of the evaluated code
    """
    escaped_script = 'JSON.stringify(eval("{0}"))'.format(escape_string(script))
    return gui.evaluate_js(escaped_script, uid)


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


def webview_ready(timeout=None):
    """
    :param delay: optional timeout
    :return: True when the last opened window is ready. False if the timeout is reached, when the timeout parameter is provided.
    Until then blocks the calling thread.
    """
    return _webview_ready.wait(timeout)


def _js_bridge_call(uid, api_instance, func_name, param):
    def _call():
        result = json.dumps(function(func_params))
        code = 'window.pywebview._returnValues["{0}"] = {{ isSet: true, value: {1}}}'.format(func_name, escape_line_breaks(result))
        evaluate_js(code, uid)

    function = getattr(api_instance, func_name, None)

    if function is not None:
        try:
            func_params = param if not param else json.loads(param)
            t = Thread(target=_call)
            t.start()
        except Exception as e:
            logger.exception('Error occurred while evaluating function {0}'.format(func_name))
    else:
        logger.error('Function {}() does not exist'.format(func_name))
