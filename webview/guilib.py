from __future__ import annotations

import logging
import os
import platform
import sys
from types import ModuleType
from typing import Any, Callable, cast

from typing_extensions import Literal, TypeAlias

from webview import WebViewException

GUIType: TypeAlias = Literal['qt', 'gtk', 'cef', 'mshtml', 'edgechromium', 'android']

logger = logging.getLogger('pywebview')
guilib: ModuleType | None = None
forced_gui_: GUIType | None = None


def initialize(forced_gui: GUIType | None = None):
    def import_android():
        global guilib

        try:
            import webview.platforms.android as guilib
            logger.debug('Using Kivy')
            return True
        except (ImportError, ValueError):
            logger.exception('Kivy cannot be loaded')
            return False

    def import_gtk():
        global guilib

        try:
            import webview.platforms.gtk as guilib

            logger.debug('Using GTK')
            return True
        except (ImportError, ValueError):
            logger.exception('GTK cannot be loaded')
            return False

    def import_qt():
        global guilib

        try:
            import webview.platforms.qt as guilib

            return True
        except ImportError:
            logger.exception('QT cannot be loaded')
            return False

    def import_cocoa():
        global guilib

        try:
            import webview.platforms.cocoa as guilib

            return True
        except ImportError:
            logger.exception('PyObjC cannot be loaded')

            return False

    def import_winforms():
        global guilib

        try:
            import webview.platforms.winforms as guilib

            return True
        except ImportError:
            logger.exception('pythonnet cannot be loaded')
            return False

    def try_import(guis: list[Callable[[], Any]]) -> bool:
        while guis:
            import_func = guis.pop(0)

            if import_func():
                return True

        return False

    global forced_gui_

    if not forced_gui:
        forced_gui = 'qt' if 'KDE_FULL_SESSION' in os.environ else None
        forced_gui = cast(
            GUIType,
            os.environ['PYWEBVIEW_GUI'].lower()
            if 'PYWEBVIEW_GUI' in os.environ
            and os.environ['PYWEBVIEW_GUI'].lower()
            in ['qt', 'gtk', 'cef', 'mshtml', 'edgechromium']
            else forced_gui,
        )

    forced_gui_ = forced_gui

    if platform.system() == 'Darwin':
        if forced_gui == 'qt':
            guis = [import_qt, import_cocoa]
        else:
            guis = [import_cocoa, import_qt]

        if not try_import(guis):
            raise WebViewException(
                'You must have either PyObjC (for Cocoa support) or Qt with Python bindings installed in order to use pywebview.'
            )

    elif hasattr(sys, 'getandroidapilevel'):
        try_import([import_android])

    elif platform.system() == 'Linux' or platform.system() == 'OpenBSD':
        if forced_gui == 'qt':
            guis = [import_qt, import_gtk]
        else:
            guis = [import_gtk, import_qt]

        if not try_import(guis):
            raise WebViewException(
                'You must have either QT or GTK with Python extensions installed in order to use pywebview.'
            )

    elif platform.system() == 'Windows':
        if forced_gui == 'qt':
            guis = [import_qt]
        else:
            guis = [import_winforms]

        if not try_import(guis):
            raise WebViewException('You must have pythonnet installed in order to use pywebview.')
    else:
        raise WebViewException(
            'Unsupported platform. Only Windows, Linux, OS X, OpenBSD are supported.'
        )

    guilib.setup_app()
    return guilib
