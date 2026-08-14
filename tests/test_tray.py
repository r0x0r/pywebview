import sys

import pytest

import webview.tray as tray
from webview.errors import WebViewException
from webview.menu import MenuAction, MenuSeparator


class TestTrayDispatch:
    def test_unsupported_platform(self, monkeypatch):
        monkeypatch.setattr(sys, 'platform', 'freebsd13')
        with pytest.raises(WebViewException):
            tray.create_tray_icon('/tmp/icon.png')


class TestLinuxTrayBackendUnavailable:
    def test_raises_clear_error_without_gi(self, monkeypatch):
        monkeypatch.setattr(sys, 'platform', 'linux')

        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == 'gi':
                raise ImportError('mocked: gi not installed')
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, '__import__', fake_import)

        with pytest.raises(WebViewException, match='PyGObject'):
            tray.create_tray_icon('/tmp/icon.png')


class TestLinuxTrayMenuConstruction:
    """
    Exercises _LinuxTray's menu-building logic against a fake Gtk-like
    object, so this runs without a real GTK/display environment.
    """

    class _FakeMenuItem:
        def __init__(self, label=None):
            self.label = label
            self.handlers = {}

        def connect(self, signal, handler):
            self.handlers[signal] = handler

    class _FakeSeparator:
        pass

    class _FakeMenu:
        def __init__(self):
            self.children = []

        def append(self, item):
            self.children.append(item)

        def show_all(self):
            pass

    class _FakeStatusIcon:
        def __init__(self):
            self.visible = False
            self.icon_file = None
            self.tooltip = None
            self.signals = {}

        def set_from_file(self, path):
            self.icon_file = path

        def set_tooltip_text(self, text):
            self.tooltip = text

        def set_visible(self, value):
            self.visible = value

        def connect(self, signal, handler):
            self.signals[signal] = handler

    def _make_fake_gtk_module(self):
        class FakeGtk:
            StatusIcon = TestLinuxTrayMenuConstruction._FakeStatusIcon
            Menu = TestLinuxTrayMenuConstruction._FakeMenu
            MenuItem = TestLinuxTrayMenuConstruction._FakeMenuItem
            SeparatorMenuItem = TestLinuxTrayMenuConstruction._FakeSeparator

        return FakeGtk

    def test_menu_items_built_and_actions_wired(self, monkeypatch):
        monkeypatch.setattr(sys, 'platform', 'linux')

        calls = []

        def action():
            calls.append('clicked')

        menu_items = [MenuAction('Open', action), MenuSeparator(), MenuAction('Quit', action)]

        impl = tray._LinuxTray.__new__(tray._LinuxTray)
        impl._Gtk = self._make_fake_gtk_module()
        impl._menu = None
        impl.set_menu(menu_items)

        assert len(impl._menu.children) == 3
        assert isinstance(impl._menu.children[1], TestLinuxTrayMenuConstruction._FakeSeparator)

        # Simulate a click on the first menu item
        first_item = impl._menu.children[0]
        handler = first_item.handlers['activate']
        handler(first_item)

        # _run_callback spawns a thread; give it a moment to run
        import time

        time.sleep(0.1)
        assert calls == ['clicked']
