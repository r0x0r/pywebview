"""
(C) 2014-2019 Roman Sirokov and contributors
Licensed under BSD license

http://github.com/imattau/pywebview2/

System tray / menu bar icon support.

Menu items reuse webview.menu.MenuAction/MenuSeparator, matching the window
menu bar's vocabulary. The native menu-construction logic here mirrors the
patterns already used for the window menu bar in each webview/platforms/*.py
backend (cocoa's generic target-action handler keyed by a representedObject
id, GTK's per-item activate signal, WinForms' per-item Click lambda), but is
implemented standalone since those functions are tightly coupled to
window/menu-bar setup (see e.g. winforms.py's set_window_menu) rather than
reusable as-is for a tray's context menu.
"""

from __future__ import annotations

import sys
import threading
from typing import Callable

from webview.errors import WebViewException
from webview.menu import MenuAction, MenuSeparator


class TrayIcon:
    """A system tray / menu bar icon. Create via webview.tray.create_tray_icon()."""

    def __init__(
        self,
        icon_path: str,
        menu_items: list[MenuAction | MenuSeparator] | None = None,
        on_click: Callable[[], None] | None = None,
        tooltip: str = 'pywebview2',
    ) -> None:
        self.icon_path = icon_path
        self.menu_items = menu_items or []
        self.on_click = on_click
        self.tooltip = tooltip
        self._impl = _create_impl(self)

    def set_menu(self, menu_items: list[MenuAction | MenuSeparator]) -> None:
        """Replace the tray icon's context menu."""
        self.menu_items = menu_items
        self._impl.set_menu(menu_items)

    def set_icon(self, icon_path: str) -> None:
        """Change the tray icon's image."""
        self.icon_path = icon_path
        self._impl.set_icon(icon_path)

    def set_tooltip(self, tooltip: str) -> None:
        """Change the tray icon's tooltip text."""
        self.tooltip = tooltip
        self._impl.set_tooltip(tooltip)

    def remove(self) -> None:
        """Remove the tray icon."""
        self._impl.remove()


def create_tray_icon(
    icon_path: str,
    menu_items: list[MenuAction | MenuSeparator] | None = None,
    on_click: Callable[[], None] | None = None,
    tooltip: str = 'pywebview2',
) -> TrayIcon:
    """
    Create and show a system tray / menu bar icon. Must be called after the
    native GUI loop has started (i.e. after webview.start() has begun
    running), since the tray icon is driven by the same native event loop as
    the window backend.

    :param icon_path: Path to the icon image file (.ico on Windows, any
        image AppKit/GTK can load on macOS/Linux).
    :param menu_items: A list of MenuAction/MenuSeparator instances shown in
        the tray icon's right-click (or left-click, on macOS) context menu.
    :param on_click: Callback invoked when the tray icon itself is clicked
        (left-click). Not supported the same way on every platform -- on
        macOS a click always opens the menu if one is set.
    :param tooltip: Tooltip text shown on hover.
    :return: A TrayIcon instance.
    """
    return TrayIcon(icon_path, menu_items, on_click, tooltip)


def _create_impl(tray: TrayIcon):
    if sys.platform == 'darwin':
        return _CocoaTray(tray)
    elif sys.platform == 'win32':
        return _WindowsTray(tray)
    elif sys.platform.startswith('linux'):
        return _LinuxTray(tray)
    else:
        raise WebViewException(f'System tray is not supported on platform {sys.platform!r}')


def _run_callback(fn: Callable[[], None]) -> None:
    threading.Thread(target=fn, daemon=True).start()


# -- macOS: NSStatusBar + NSMenu, via pyobjc (already a dependency) ------------------------

_cocoa_handler_class = None


def _get_cocoa_handler_class(AppKit, objc):
    global _cocoa_handler_class
    if _cocoa_handler_class is not None:
        return _cocoa_handler_class

    class PywebviewTrayHandler(AppKit.NSObject):
        def init(self):
            self = objc.super(PywebviewTrayHandler, self).init()
            if self is None:
                return None
            self.actions = {}
            self.click_callback = None
            return self

        def handleMenuAction_(self, sender):
            fn = self.actions.get(sender.representedObject())
            if fn:
                _run_callback(fn)

        def handleClick_(self, sender):
            if self.click_callback:
                _run_callback(self.click_callback)

    _cocoa_handler_class = PywebviewTrayHandler
    return _cocoa_handler_class


class _CocoaTray:
    def __init__(self, tray: TrayIcon) -> None:
        try:
            import AppKit
            import objc
        except ImportError as e:
            raise WebViewException('System tray requires pyobjc on macOS.') from e

        self._AppKit = AppKit
        self._actions: dict[str, Callable[[], None]] = {}

        handler_cls = _get_cocoa_handler_class(AppKit, objc)
        self._handler = handler_cls.alloc().init()

        status_bar = AppKit.NSStatusBar.systemStatusBar()
        self._status_item = status_bar.statusItemWithLength_(AppKit.NSVariableStatusItemLength)
        self._status_item.retain()

        self.set_icon(tray.icon_path)
        self.set_tooltip(tray.tooltip)

        if tray.on_click:
            self._handler.click_callback = tray.on_click
            self._status_item.button().setTarget_(self._handler)
            self._status_item.button().setAction_('handleClick:')

        self.set_menu(tray.menu_items)

    def set_icon(self, icon_path: str) -> None:
        image = self._AppKit.NSImage.alloc().initByReferencingFile_(icon_path)
        self._status_item.button().setImage_(image)

    def set_tooltip(self, tooltip: str) -> None:
        self._status_item.button().setToolTip_(tooltip)

    def set_menu(self, menu_items: list[MenuAction | MenuSeparator]) -> None:
        menu = self._AppKit.NSMenu.alloc().init()
        self._actions = {}

        for index, item in enumerate(menu_items):
            if isinstance(item, MenuSeparator):
                menu.addItem_(self._AppKit.NSMenuItem.separatorItem())
            elif isinstance(item, MenuAction):
                action_id = f'{index}:{item.title}'
                self._actions[action_id] = item.function
                menu_item = self._AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                    item.title, 'handleMenuAction:', ''
                )
                menu_item.setTarget_(self._handler)
                menu_item.setRepresentedObject_(action_id)
                menu.addItem_(menu_item)

        self._handler.actions = self._actions
        self._status_item.setMenu_(menu)

    def remove(self) -> None:
        self._AppKit.NSStatusBar.systemStatusBar().removeStatusItem_(self._status_item)


# -- Windows: NotifyIcon + ContextMenuStrip, via pythonnet (already a dependency) ----------


class _WindowsTray:
    def __init__(self, tray: TrayIcon) -> None:
        try:
            import clr

            clr.AddReference('System.Windows.Forms')
            clr.AddReference('System.Drawing')
            import System.Windows.Forms as WinForms
            from System.Drawing import Icon
        except ImportError as e:
            raise WebViewException('System tray requires pythonnet on Windows.') from e

        self._WinForms = WinForms
        self._Icon = Icon
        self._on_click = tray.on_click

        self._notify_icon = WinForms.NotifyIcon()
        self.set_icon(tray.icon_path)
        self.set_tooltip(tray.tooltip)
        self._notify_icon.Visible = True

        if tray.on_click:
            self._notify_icon.Click += self._handle_click

        self.set_menu(tray.menu_items)

    def _handle_click(self, sender, event) -> None:
        _run_callback(self._on_click)

    def _create_action_item(self, item: MenuAction):
        action_item = self._WinForms.ToolStripMenuItem(item.title)
        fn = item.function

        def _handler(sender, event, fn=fn):
            _run_callback(fn)

        action_item.Click += _handler
        return action_item

    def set_menu(self, menu_items: list[MenuAction | MenuSeparator]) -> None:
        menu = self._WinForms.ContextMenuStrip()
        for item in menu_items:
            if isinstance(item, MenuSeparator):
                menu.Items.Add(self._WinForms.ToolStripSeparator())
            elif isinstance(item, MenuAction):
                menu.Items.Add(self._create_action_item(item))
        self._notify_icon.ContextMenuStrip = menu

    def set_icon(self, icon_path: str) -> None:
        self._notify_icon.Icon = self._Icon(icon_path)

    def set_tooltip(self, tooltip: str) -> None:
        self._notify_icon.Text = tooltip[:63]  # NotifyIcon.Text is limited to 63 characters

    def remove(self) -> None:
        self._notify_icon.Visible = False
        self._notify_icon.Dispose()


# -- Linux: Gtk.StatusIcon, via PyGObject (already the `gtk` extra) ------------------------
# Gtk.StatusIcon has been deprecated since GTK 3.14 and some desktop
# environments (e.g. stock GNOME) don't render it without a shell extension.
# It's used here anyway since it requires nothing beyond the `gtk` extra
# already needed for the GTK window backend -- AppIndicator3 would work more
# reliably on GNOME but needs an additional system package that isn't
# guaranteed present.


class _LinuxTray:
    def __init__(self, tray: TrayIcon) -> None:
        try:
            import gi

            gi.require_version('Gtk', '3.0')
            from gi.repository import Gtk
        except (ImportError, ValueError) as e:
            raise WebViewException('System tray requires PyGObject (GTK) on Linux.') from e

        self._Gtk = Gtk
        self._on_click = tray.on_click
        self._menu = None

        self._status_icon = Gtk.StatusIcon()
        self.set_icon(tray.icon_path)
        self.set_tooltip(tray.tooltip)

        if tray.on_click:
            self._status_icon.connect('activate', self._handle_click)

        self._status_icon.connect('popup-menu', self._handle_popup_menu)
        self.set_menu(tray.menu_items)
        self._status_icon.set_visible(True)

    def _handle_click(self, icon) -> None:
        _run_callback(self._on_click)

    def _handle_popup_menu(self, icon, button, time) -> None:
        if self._menu is not None:
            self._menu.popup(None, None, self._Gtk.StatusIcon.position_menu, icon, button, time)

    def set_menu(self, menu_items: list[MenuAction | MenuSeparator]) -> None:
        menu = self._Gtk.Menu()
        for item in menu_items:
            if isinstance(item, MenuSeparator):
                menu.append(self._Gtk.SeparatorMenuItem())
            elif isinstance(item, MenuAction):
                menu_item = self._Gtk.MenuItem(label=item.title)
                fn = item.function
                menu_item.connect('activate', lambda _widget, fn=fn: _run_callback(fn))
                menu.append(menu_item)
        menu.show_all()
        self._menu = menu

    def set_icon(self, icon_path: str) -> None:
        self._status_icon.set_from_file(icon_path)

    def set_tooltip(self, tooltip: str) -> None:
        self._status_icon.set_tooltip_text(tooltip)

    def remove(self) -> None:
        self._status_icon.set_visible(False)
