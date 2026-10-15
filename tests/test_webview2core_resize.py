"""
Unit tests for the pywebviewStartResize bridge message.

Starting the native sizing loop drives real window geometry from a page, so the
session token gate is worth pinning down. No window is involved, which is why
these are unit tests rather than the usual run_test() smoke tests.

webview.platforms.webview2core imports webview.platforms.win32, which uses
ctypes.windll and therefore cannot even be imported outside Windows, so this
whole module is skipped everywhere else.
"""

import json
import sys
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != 'win32',
    reason='webview2core.py imports webview.platforms.win32, which requires ctypes.windll',
)

HTTOPLEFT = 13
DRAG_HWND = 0x1234


def _route(monkeypatch, token, code=HTTOPLEFT):
    from webview.platforms import webview2core

    calls = []
    monkeypatch.setattr(webview2core, 'start_sizing', lambda hwnd, hit: calls.append((hwnd, hit)))

    core = SimpleNamespace(
        pywebview_window=SimpleNamespace(gui=SimpleNamespace(renderer='edgechromium')),
        _drag_hwnd=DRAG_HWND,
    )
    # api.js posts the parameter list as a JSON string of its own
    message = json.dumps(['pywebviewStartResize', json.dumps([code]), 'resize', token])
    webview2core.WebView2Core._route_script_message(core, message, lambda: None)
    return calls


def test_sizing_loop_is_started_for_the_session_token(monkeypatch):
    from webview.util import _TOKEN

    assert _route(monkeypatch, _TOKEN) == [(DRAG_HWND, HTTOPLEFT)]


def test_sizing_loop_is_not_started_without_a_token(monkeypatch):
    assert _route(monkeypatch, '') == []


def test_sizing_loop_is_not_started_for_a_forged_token(monkeypatch):
    assert _route(monkeypatch, '0123456789abcdef') == []


def test_hit_code_is_passed_through(monkeypatch):
    from webview.util import _TOKEN

    assert _route(monkeypatch, _TOKEN, code=17) == [(DRAG_HWND, 17)]
