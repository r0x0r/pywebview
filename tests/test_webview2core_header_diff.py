"""
Unit tests for WebView2Core._compute_request_header_diff() - pure dict-diffing
logic shared by the WinForms/EdgeChromium and WinUI3 backends.

webview.platforms.webview2core imports webview.platforms.win32, which uses
ctypes.windll and therefore cannot even be imported outside Windows, so this
whole module (including the import of the class under test) is skipped
everywhere else.
"""

import sys
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != 'win32',
    reason='webview2core.py imports webview.platforms.win32, which requires ctypes.windll',
)


def _diff(handler, original, uri='http://example.com/', method='GET'):
    from webview.event import Event
    from webview.platforms.webview2core import WebView2Core

    request_sent = Event(None, True)  # locking, so .set() runs `handler` inline
    request_sent += handler
    core = SimpleNamespace(
        pywebview_window=SimpleNamespace(events=SimpleNamespace(request_sent=request_sent))
    )
    return WebView2Core._compute_request_header_diff(core, original, uri, method)


class TestComputeRequestHeaderDiff:
    def test_no_change_returns_none(self):
        result = _diff(lambda request: None, {'Accept': 'text/html'})
        assert result is None

    def test_adding_a_header(self):
        def handler(request):
            request.headers['X-Extra'] = 'added'

        extra, missing = _diff(handler, {'Accept': 'text/html'})
        assert extra == {'X-Extra': 'added'}
        assert missing == set()

    def test_removing_a_header(self):
        def handler(request):
            del request.headers['Accept']

        extra, missing = _diff(handler, {'Accept': 'text/html', 'User-Agent': 'test'})
        assert extra == {}
        assert missing == {'Accept'}

    def test_changing_a_headers_value(self):
        def handler(request):
            request.headers['User-Agent'] = 'custom-agent'

        extra, missing = _diff(handler, {'User-Agent': 'original'})
        assert extra == {'User-Agent': 'custom-agent'}
        assert missing == set()

    def test_casing_only_rename_is_not_treated_as_add_and_remove(self):
        # HTTP header names are case-insensitive; WebView2 treats 'User-Agent'
        # and 'user-agent' as the same header, so this must appear only in
        # `extra` (to be re-set under the new casing) and NOT in `missing`
        # (which would otherwise delete the header the rename just re-added).
        def handler(request):
            value = request.headers.pop('User-Agent')
            request.headers['user-agent'] = value

        extra, missing = _diff(handler, {'User-Agent': 'test-value'})
        assert extra == {'user-agent': 'test-value'}
        assert missing == set()
