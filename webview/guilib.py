import logging
import os
import platform

from webview.util import WebViewException

logger = logging.getLogger('pywebview')
import importlib


def initialize(gui=None):
    """
    Load an implementation for webview
    :param gui: One of the following types:
        None = use the default implementation for the current platform
        str = a single gui implementation to use
        list[str] = the implementations to use, in the order to try them
    :return: a python module.
    """
    if gui is not None:
        if isinstance(gui, str):
            guis = [gui]
        else:
            guis = list(gui)
    elif 'PYWEBVIEW_GUI' in os.environ:
        guis = [os.environ['PYWEBVIEW_GUI'].lower()]
    elif platform.system() == 'Darwin':
        guis = ['cocoa', 'qt']
    elif platform.system() == 'Windows':
        guis = ['winforms']
    else:
        guis = ['gtk', 'qt']

    guilib = None
    errors = []
    for a_gui in guis:
        try:
            if a_gui == 'cef' and platform.system == 'Windows':
                import webview.platforms.winforms as guilib
                guilib.use_cef()
            else:
                guilib = importlib.import_module('webview.platforms.' + a_gui)
        except Exception as e:
            errors.append(str(e))
        if guilib is not None:
            break

    if guilib is None:
        raise WebViewException(
            'Could not load any implementations.\nTried {}\nErrors:\n{}'.format(
                ', '.join(guis),
                '\n'.join(errors)
            )
        )

    return guilib
