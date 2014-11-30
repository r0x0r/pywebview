#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
pywebview is a lightweight cross-platform wrapper around a webview component that allows to display HTML content in its
own dedicated window. Works on Windows, OS X and Linux and compatible with Python 2 and 3.

(C) 2014 Roman Sirokov
Licensed under BSD license

http://github.com/r0x0r/pywebview/
"""


import platform
import os
import sys
import logging

logger = logging.getLogger(__name__)
#logging.basicConfig(level=logging.INFO)

if platform.system() == "Darwin":
    import webview.cocoa as gui
elif platform.system() == "Linux":
    try:
        #Try QT first
        import webview.qt as gui
    except Exception as e:
        logger.warning("QT not found")
        import_error = True
    else:
        import_error = False

    if not import_error:
        try:
            # If QT is not found, then try GTK
            import webview.gtk as gui
        except Exception as e:
            # Panic
            logger.error("GTK not found")
            raise Exception("You must have either QT or GTK with Python extensions installed in order to this component.")

elif platform.system() == "Windows":
    import webview.win32 as gui
else:
    raise Exception("Unsupported platform. Only Windows, Linux and OS X are supported.")




def load_url(url):
    """
    Load a new URL into a previously created WebView window. This function must be invoked after WebView windows is
    created with create_window(). Otherwise an exception is thrown.
    :param url: url to load
    """
    gui.load_url(url)


def create_window(title, url, width=800, height=600, resizable=True, fullscreen=False):
    """
    Create a web view window using a native GUI. The execution blocks after this function is invoked, so other
    program logic must be executed in a separate thread.
    :param title: Window title
    :param url: URL to load
    :param width: Optional window width (default: 800px)
    :param height: Optional window height (default: 600px)
    :param resizable True if window can be resized, False otherwise. Default is True.
    :return:
    """
    gui.create_window(_make_unicode(title), _transform_url(url), width, height, resizable, fullscreen)


def _make_unicode(string):
    """
    Python 2 and 3 compatibility function that converts a string to Unicode. In case of Unicode, the string is returned
    unchanged
    :param string: input string
    :return: Unicode string
    """
    if sys.version < '3' and isinstance(string, str):
        return unicode(string.decode('utf-8'))

    return string


def _transform_url(url):
    if url.find(":") == -1:
        return 'file://' + os.path.abspath(url)
    else:
        return url
