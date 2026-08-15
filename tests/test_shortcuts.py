import os
import sys
import time

import pytest

import webview.shortcuts as shortcuts
from webview.errors import WebViewException


@pytest.fixture(autouse=True)
def _cleanup_registry():
    yield
    shortcuts.unregister_all()


class TestParseShortcut:
    def test_single_modifier(self):
        modifiers, key = shortcuts._parse_shortcut('ctrl+s')
        assert modifiers == frozenset({'ctrl'})
        assert key == 's'

    def test_multiple_modifiers(self):
        modifiers, key = shortcuts._parse_shortcut('ctrl+shift+s')
        assert modifiers == frozenset({'ctrl', 'shift'})
        assert key == 's'

    def test_no_modifiers(self):
        modifiers, key = shortcuts._parse_shortcut('f5')
        assert modifiers == frozenset()
        assert key == 'f5'

    def test_modifier_aliases(self):
        for alias in ('ctrl', 'control'):
            modifiers, _ = shortcuts._parse_shortcut(f'{alias}+a')
            assert modifiers == frozenset({'ctrl'})
        for alias in ('alt', 'option'):
            modifiers, _ = shortcuts._parse_shortcut(f'{alias}+a')
            assert modifiers == frozenset({'alt'})
        for alias in ('super', 'cmd', 'command', 'win', 'meta'):
            modifiers, _ = shortcuts._parse_shortcut(f'{alias}+a')
            assert modifiers == frozenset({'super'})

    def test_cmdorctrl_resolves_per_platform(self, monkeypatch):
        monkeypatch.setattr(sys, 'platform', 'darwin')
        modifiers, _ = shortcuts._parse_shortcut('cmdorctrl+k')
        assert modifiers == frozenset({'super'})

        monkeypatch.setattr(sys, 'platform', 'win32')
        modifiers, _ = shortcuts._parse_shortcut('cmdorctrl+k')
        assert modifiers == frozenset({'ctrl'})

    def test_case_insensitive(self):
        modifiers, key = shortcuts._parse_shortcut('CTRL+SHIFT+S')
        assert modifiers == frozenset({'ctrl', 'shift'})
        assert key == 's'

    def test_unknown_modifier_raises(self):
        with pytest.raises(WebViewException, match='Unknown modifier'):
            shortcuts._parse_shortcut('foo+s')

    def test_empty_shortcut_raises(self):
        with pytest.raises(WebViewException):
            shortcuts._parse_shortcut('')


class TestRegistryDispatch:
    """
    Tests for the shared registry logic in register/unregister/is_registered
    (duplicate detection, no-op unregister, unregister_all) -- these don't
    care which OS backend is used, so the actual per-platform register/
    unregister functions are faked out here rather than exercising the real
    native backend (which may not have its optional dependency installed,
    e.g. python-xlib on a Linux CI job that didn't install
    pywebview2[shortcuts]).
    """

    @pytest.fixture(autouse=True)
    def _fake_backend(self, monkeypatch):
        counter = iter(range(1, 1000))
        monkeypatch.setattr(shortcuts, '_linux_register', lambda *a: next(counter))
        monkeypatch.setattr(shortcuts, '_linux_unregister', lambda *a: None)
        monkeypatch.setattr(shortcuts, '_macos_register', lambda *a: next(counter))
        monkeypatch.setattr(shortcuts, '_macos_unregister', lambda *a: None)
        monkeypatch.setattr(shortcuts, '_windows_register', lambda *a: next(counter))
        monkeypatch.setattr(shortcuts, '_windows_unregister', lambda *a: None)
        yield

    def test_unsupported_platform(self, monkeypatch):
        monkeypatch.setattr(sys, 'platform', 'freebsd13')
        with pytest.raises(WebViewException):
            shortcuts.register('ctrl+s', lambda: None)

    def test_duplicate_registration_raises(self):
        shortcuts.register('ctrl+alt+z', lambda: None)
        with pytest.raises(WebViewException, match='already registered'):
            shortcuts.register('ctrl+alt+z', lambda: None)

    def test_unregister_unknown_is_noop(self):
        shortcuts.unregister('ctrl+never+registered')

    def test_is_registered(self):
        assert shortcuts.is_registered('ctrl+alt+y') is False
        shortcuts.register('ctrl+alt+y', lambda: None)
        assert shortcuts.is_registered('ctrl+alt+y') is True
        shortcuts.unregister('ctrl+alt+y')
        assert shortcuts.is_registered('ctrl+alt+y') is False

    def test_unregister_all(self):
        shortcuts.register('ctrl+alt+1', lambda: None)
        shortcuts.register('ctrl+alt+2', lambda: None)
        shortcuts.unregister_all()
        assert not shortcuts.is_registered('ctrl+alt+1')
        assert not shortcuts.is_registered('ctrl+alt+2')


@pytest.mark.skipif(
    sys.platform != 'linux' or not os.environ.get('DISPLAY'),
    reason='requires a live X11 display',
)
class TestLinuxRealX11Integration:
    """
    Exercises the real XGrabKey path end-to-end against a live X server:
    registers a global shortcut, injects the actual key combo via the XTest
    extension, and verifies the callback fires (and stops firing after
    unregister). Requires python-xlib.
    """

    def test_shortcut_fires_on_real_keypress(self):
        pytest.importorskip('Xlib')
        from Xlib import XK, X, display
        from Xlib.ext import xtest

        d = display.Display()
        # A bare X session may have no window focus at all, in which case
        # X11 discards key events entirely regardless of any grab -- set
        # focus to the root window so injected events have somewhere to go.
        d.set_input_focus(d.screen().root, X.RevertToPointerRoot, X.CurrentTime)
        d.sync()

        fired = []
        shortcuts.register('ctrl+shift+t', lambda: fired.append(True))
        time.sleep(0.3)

        ctrl_kc = d.keysym_to_keycode(XK.string_to_keysym('Control_L'))
        shift_kc = d.keysym_to_keycode(XK.string_to_keysym('Shift_L'))
        t_kc = d.keysym_to_keycode(XK.string_to_keysym('t'))

        def _press_combo():
            xtest.fake_input(d, X.KeyPress, ctrl_kc)
            xtest.fake_input(d, X.KeyPress, shift_kc)
            xtest.fake_input(d, X.KeyPress, t_kc)
            d.sync()
            time.sleep(0.1)
            xtest.fake_input(d, X.KeyRelease, t_kc)
            xtest.fake_input(d, X.KeyRelease, shift_kc)
            xtest.fake_input(d, X.KeyRelease, ctrl_kc)
            d.sync()

        _press_combo()
        time.sleep(0.5)
        assert fired == [True]

        shortcuts.unregister('ctrl+shift+t')
        fired.clear()

        _press_combo()
        time.sleep(0.4)
        assert fired == []
