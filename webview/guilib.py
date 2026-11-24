from __future__ import annotations

import logging
import os
import platform
import sys
from types import ModuleType
from typing import Literal, TypeAlias, cast, get_args

from webview import WebViewException

GUIType: TypeAlias = Literal['qt', 'gtk', 'edgechromium', 'android', 'cocoa', 'winui3']
GUI_TYPES = list(get_args(GUIType))
# Removed renderers. They are still accepted so that the fallback warning is logged.
RETIRED_GUI_TYPES = ('mshtml', 'cef')

logger = logging.getLogger('pywebview')
guilib: ModuleType | None = None
forced_gui_: GUIType | None = None


# Name of the library each backend needs and the errors it raises when that library is missing
_BACKENDS: dict[str, tuple[str, tuple[type[Exception], ...]]] = {
    'android': ('Kivy', (ImportError, ValueError)),
    'cocoa': ('PyObjC', (ImportError, ValueError)),
    'gtk': ('GTK', (ImportError, ValueError)),
    'qt': ('QT', (ImportError, ValueError)),
    'winforms': ('pythonnet', (ImportError, RuntimeError)),
    'winui3': ('WinRT', (ImportError,)),
}


def _import_backend(name: str) -> ModuleType:
    # Plain import statements, so that freezers such as PyInstaller find the backends
    if name == 'android':
        import webview.platforms.android as android

        return android
    if name == 'cocoa':
        import webview.platforms.cocoa as cocoa

        return cocoa
    if name == 'gtk':
        import webview.platforms.gtk as gtk

        return gtk
    if name == 'qt':
        import webview.platforms.qt as qt

        return qt
    if name == 'winforms':
        import webview.platforms.winforms as winforms

        return winforms
    import webview.platforms.winui3 as winui3

    return winui3


def _try_import(names: list[str]) -> bool:
    """Import the first backend in names that loads and make it the GUI library."""
    global guilib

    for name in names:
        library, errors = _BACKENDS[name]
        try:
            guilib = _import_backend(name)
            logger.debug(f'Using {library}')
            return True
        except errors:
            logger.exception(f'{library} cannot be loaded')
    return False


def initialize(forced_gui: GUIType | None = None):
    global forced_gui_

    if not forced_gui:
        env_gui = os.environ.get('PYWEBVIEW_GUI', '').lower()
        if env_gui in (*GUI_TYPES, *RETIRED_GUI_TYPES):
            forced_gui = cast(GUIType, env_gui)
        elif 'KDE_FULL_SESSION' in os.environ:
            forced_gui = 'qt'

    if forced_gui in RETIRED_GUI_TYPES:
        logger.warning(
            f'{forced_gui.upper()} support has been removed. Using the default renderer instead.'
        )
        forced_gui = None

    forced_gui_ = forced_gui

    if platform.system() == 'Darwin':
        if forced_gui == 'qt':
            guis = ['qt', 'cocoa']
        else:
            guis = ['cocoa', 'qt']

        if not _try_import(guis):
            raise WebViewException(
                'You must have either PyObjC (for Cocoa support) or Qt with Python bindings installed in order to use pywebview.'
            )

    elif hasattr(sys, 'getandroidapilevel'):
        _try_import(['android'])

    elif platform.system() == 'Linux' or platform.system() == 'OpenBSD':
        if forced_gui == 'qt':
            guis = ['qt', 'gtk']
        else:
            guis = ['gtk', 'qt']

        if not _try_import(guis):
            raise WebViewException(
                'You must have either QT or GTK with Python extensions installed in order to use pywebview.'
            )

    elif platform.system() == 'Windows':
        if forced_gui == 'qt':
            guis = ['qt', 'winforms', 'winui3']
        elif forced_gui == 'winui3':
            # Explicitly requested: don't silently fall back to WinForms if
            # the WinUI 3 import fails, or callers asking for winui3 could
            # unknowingly get a different renderer instead.
            guis = ['winui3']
        elif forced_gui == 'edgechromium':
            # Explicitly requested the WinForms renderer: don't silently
            # fall back to WinUI 3 if it fails to load either, for the same
            # reason as the winui3 case above.
            guis = ['winforms']
        else:
            guis = ['winforms', 'winui3']

        if not _try_import(guis):
            if forced_gui == 'winui3':
                # Only the winui3 extra could satisfy this branch — pythonnet
                # wouldn't help, and mentioning it would send the user
                # chasing the wrong dependency.
                raise WebViewException(
                    'You must have Python 3.11 or newer, the pywebview[winui3] extra, the Edge '
                    'WebView2 Runtime and Windows App Runtime 2.x installed, in order to use '
                    'pywebview.'
                )
            elif forced_gui == 'edgechromium':
                # Only pythonnet could satisfy this branch — fallback to
                # winui3 is intentionally disabled above, so mentioning its
                # extra here would be equally misleading.
                raise WebViewException(
                    'You must have pythonnet and the Edge WebView2 Runtime installed in order '
                    'to use pywebview.'
                )
            raise WebViewException(
                'You must have the Edge WebView2 Runtime and either pythonnet, or the '
                'pywebview[winui3] extra and Windows App Runtime installed, in order to use '
                'pywebview.'
            )
    else:
        raise WebViewException(
            'Unsupported platform. Only Windows, Linux, OS X, OpenBSD are supported.'
        )

    assert guilib is not None
    guilib.setup_app()
    return guilib
