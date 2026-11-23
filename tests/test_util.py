import importlib
import json
import logging
import os
import re
import sys
import threading
from queue import Empty, Queue
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest

import webview
from webview import util
from webview.errors import SecurityException, WebViewException
from webview.util import (
    _TOKEN,
    create_cookie,
    is_js_bridge_token_valid,
    js_bridge_call,
    parse_file_type,
)

# Many of these tests exercise error paths that log tracebacks on purpose
pytestmark = pytest.mark.usefixtures('quiet_console_log')

TRUSTED_URL = 'https://trusted.example/app'


class _SyncThread:
    def __init__(self, target, args=(), **kwargs):
        self._target, self._args = target, args

    def start(self):
        self._target(*self._args)


@pytest.fixture
def sync_threads(monkeypatch):
    """Run the threads util starts at once, so a test can tell that a call did not happen."""
    monkeypatch.setattr(util, 'Thread', _SyncThread)


def _bridge_window(url=TRUSTED_URL, restricted=False, **kwargs):
    """A window whose current document at url was injected with the token 'document-token'."""
    window = webview.create_window('Bridge', **kwargs)
    window._js_api_token = 'document-token'
    window._js_api_restricted = restricted
    window._js_api_document_url = url
    window._functions['target'] = Mock(return_value='ok')
    window.gui = Mock()  # receives the result of accepted calls
    window.events.before_load.set()
    return window


def _send(window, source_url, token='document-token'):
    """Call the exposed function 'target' from the page and return whether it ran."""
    window._functions['target'].reset_mock()
    js_bridge_call(window, 'target', [], 'value-id', token, source_url)
    return window._functions['target'].called


@pytest.mark.parametrize('error', [FileNotFoundError('missing JS'), ValueError('invalid JS')])
def test_injection_resource_failure_does_not_escape_native_callback(monkeypatch, caplog, error):
    window = SimpleNamespace(
        events=SimpleNamespace(
            before_load=threading.Event(),
            loaded=threading.Event(),
            _pywebviewready=threading.Event(),
        ),
        run_js=Mock(),
    )
    monkeypatch.setattr(util, 'load_js_files', Mock(side_effect=error))
    thread = Mock()
    monkeypatch.setattr(util, 'Thread', thread)

    util.inject_pywebview('cocoa', window)

    assert window.events.before_load.is_set()
    assert window.events.loaded.is_set()
    assert not window.events._pywebviewready.is_set()
    window.run_js.assert_not_called()
    thread.assert_not_called()
    assert 'Failed to load pywebview JavaScript' in caplog.text


@pytest.mark.parametrize('fail_on', [1, 2, None])
def test_injection_failure_releases_loaded_without_claiming_bridge_ready(monkeypatch, fail_on):
    window = SimpleNamespace(
        events=SimpleNamespace(
            before_load=threading.Event(),
            loaded=threading.Event(),
            _pywebviewready=threading.Event(),
        ),
        _expose_lock=threading.Lock(),
        _js_api=None,
        _functions={},
        _js_api_origins=set(),
        run_js=Mock(
            side_effect=[
                RuntimeError('initial injection failed') if fail_on == 1 else None,
                RuntimeError('API injection failed') if fail_on == 2 else None,
            ]
        ),
    )
    monkeypatch.setattr(util, 'load_js_files', lambda *args: ('initial JS', '%(functions)s'))
    util.inject_pywebview('cocoa', window)

    assert window.events.loaded.wait(2)
    assert window.events._pywebviewready.is_set() == (fail_on is None)
    assert window.run_js.call_count == (1 if fail_on == 1 else 2)


def test_invalid_js_template_identifies_the_resource(tmp_path, monkeypatch):
    script = tmp_path / 'customize 2.js'
    script.write_text('var selectText = %(text_select)s;', encoding='utf-8')
    monkeypatch.setattr(util, 'get_js_dir', lambda: str(tmp_path))

    with pytest.raises(WebViewException, match='customize 2.js') as caught:
        util.load_js_files(SimpleNamespace(), 'cocoa')
    assert isinstance(caught.value.__cause__, KeyError)


def test_js_dir_with_glob_metacharacters(tmp_path, monkeypatch):
    js_dir = tmp_path / 'app [1]' / 'js'
    js_dir.mkdir(parents=True)
    (js_dir / 'custom.js').write_text('var loaded = true;', encoding='utf-8')
    monkeypatch.setattr(util, 'get_js_dir', lambda: str(js_dir))

    js_code, _ = util.load_js_files(SimpleNamespace(), 'cocoa')
    assert js_code == 'var loaded = true;'


class TestParseFileType:
    @pytest.mark.parametrize(
        'file_type, expected',
        [
            ('Images (*.png)', ('Images', '*.png')),
            ('Images (*.png;*.jpg;*.gif)', ('Images', '*.png;*.jpg;*.gif')),
            # Extensions with several dots, also after the first one
            (
                'Archives (*.zip;*.tar.gz;*.backup.old.gz)',
                ('Archives', '*.zip;*.tar.gz;*.backup.old.gz'),
            ),
            ('All files (*.*)', ('All files', '*.*')),
            ('All files (*)', ('All files', '*')),
            # Digits and inner whitespace are kept in the description
            ('MP3  Audio (*.mp3)', ('MP3  Audio', '*.mp3')),
        ],
    )
    def test_valid_filter(self, file_type, expected):
        assert parse_file_type(file_type) == expected

    @pytest.mark.parametrize(
        'file_type',
        [
            '',
            'Images *.png',
            '(*.png)',
            'Images ()',
            'Images (*.png',
            'Images-Files (*.png)',
            'Images (png;jpg)',
            'Images (*png)',
            'Images (*.png;.jpg)',
        ],
    )
    def test_invalid_filter(self, file_type):
        with pytest.raises(ValueError, match='is not a valid file filter'):
            parse_file_type(file_type)


class TestCreateCookie:
    """Tests for create_cookie's handling of None-valued expires/samesite fields."""

    def _cookie_dict(self, expires):
        return {
            'name': 'foo',
            'value': 'bar',
            'path': '/',
            'domain': 'example.com',
            'expires': expires,
            'secure': False,
            'httponly': False,
        }

    def test_session_cookie_omits_expires(self):
        """expires=None (a session cookie) must not render as the literal string 'None'."""
        cookie = create_cookie(self._cookie_dict(None))
        output = cookie['foo'].output()
        assert 'expires' not in output.lower()

    def test_persistent_cookie_keeps_expires(self):
        """A real expiry string is preserved unchanged."""
        expiry = 'Wed, 21 Oct 2026 07:28:00 GMT'
        cookie = create_cookie(self._cookie_dict(expiry))
        output = cookie['foo'].output()
        assert expiry in output

    @pytest.mark.parametrize('value', ['{"key":"value","number":42}', '{ "key": "value" }'])
    def test_set_cookie_header_with_json_value(self, value):
        """GTK and Qt pass Set-Cookie header values, and SimpleCookie alone drops a JSON value."""
        header = (
            f'testJson={value}; '
            'expires=Thu, 18 Dec 2133 12:00:00 GMT; Path=/; HttpOnly; Max-Age; Secure=false'
        )
        morsel = create_cookie(header)['testJson']
        assert morsel.value == value
        assert morsel['expires'] == 'Thu, 18 Dec 2133 12:00:00 GMT'
        assert morsel['path'] == '/'
        assert morsel['httponly'] is True
        assert morsel['secure'] is True
        assert morsel['max-age'] == ''

    def test_quoted_value_with_semicolon(self):
        morsel = create_cookie('prefs="a;b"; Path=/')['prefs']
        assert morsel.value == 'a;b'
        assert morsel['path'] == '/'

    def test_zero_expiry_is_not_treated_as_session_cookie(self):
        """0 (the Unix epoch) is a real, falsy expiry - must not be normalized away like None."""
        cookie = create_cookie(self._cookie_dict(0))
        assert cookie['foo']['expires'] == 0

    def test_unspecified_samesite_is_omitted(self):
        """samesite=None (backend couldn't report a policy) must not render as 'SameSite=None'."""
        data = self._cookie_dict(None)
        cookie = create_cookie(data)
        output = cookie['foo'].output()
        assert 'samesite' not in output.lower()

    def test_explicit_samesite_is_preserved(self):
        data = self._cookie_dict(None)
        data['samesite'] = 'lax'
        cookie = create_cookie(data)
        output = cookie['foo'].output()
        assert 'samesite=lax' in output.lower()


@pytest.mark.usefixtures('sync_threads')
class TestBridgeTokenValidation:
    """Tests that bridge calls require the current document's token and a native URL."""

    @pytest.mark.parametrize(
        'token, source_url, accepted',
        [
            ('document-token', TRUSTED_URL, True),
            ('document-token', 'https://trusted.example/other-page', True),
            ('not-the-token', TRUSTED_URL, False),
            (_TOKEN, TRUSTED_URL, False),  # the session token is not a bridge token
            (None, TRUSTED_URL, False),
            ('document-token', None, False),
            ('document-token', 'https://untrusted.example', False),
        ],
    )
    def test_call_needs_the_document_token_and_url(self, token, source_url, accepted):
        assert _send(_bridge_window(), source_url, token) is accepted

    def test_navigation_revokes_document_token(self):
        window = webview.create_window('Token', html='<html></html>')
        window._js_api_token = 'old-document'
        window._js_api_pending_html = False
        window._js_api_origins.add('about:blank')
        window._invalidate_js_api()
        assert not is_js_bridge_token_valid(window, 'old-document')
        assert not util.is_js_api_allowed(window, 'about:blank')

    def test_result_is_sent_only_to_the_calling_document(self):
        window = _bridge_window()
        assert _send(window, TRUSTED_URL)

        script = window.gui.evaluate_js.call_args.args[0]
        # Not through window.evaluate_js, whose eval() the page can replace
        assert 'eval(' not in script
        assert 'window.pywebview._bridgeToken === "document-token"' in script
        assert '["https://trusted.example"]' in script

    def test_callback_id_is_a_quoted_property_key(self):
        window = _bridge_window()
        value_id = '"]; } window.captured = "secret"; //'

        js_bridge_call(window, 'target', [], value_id, 'document-token', TRUSTED_URL)

        script = window.gui.evaluate_js.call_args.args[0]
        assert f'_returnValuesCallbacks["target"][{json.dumps(value_id)}]' in script


@pytest.mark.usefixtures('sync_threads')
class TestJsBridgeHardening:
    """What a page can reach through the JS bridge and external links."""

    class Child:
        def __init__(self, calls):
            self._calls = calls

        def method(self):
            self._calls.append('child.method')

        def _hidden(self):
            self._calls.append('child._hidden')

    class Api:
        def __init__(self, calls):
            self._calls = calls
            self.child = TestJsBridgeHardening.Child(calls)

        def public(self):
            self._calls.append('public')

        def _private(self):
            self._calls.append('_private')

    def _call(self, func_name, advertised):
        """Call func_name from the page and return the API methods that ran."""
        calls = []
        window = _bridge_window()
        window._js_api = self.Api(calls)
        window._js_api_names = frozenset(advertised)
        js_bridge_call(window, func_name, [], 'value-id', 'document-token', TRUSTED_URL)
        return calls

    @pytest.mark.parametrize('func_name', ['public', 'child.method'])
    def test_advertised_name_is_dispatched(self, func_name):
        assert self._call(func_name, {'public', 'child.method'}) == [func_name]

    @pytest.mark.parametrize(
        'func_name', ['_private', 'child._hidden', '_calls.append', 'child', 'public.__call__']
    )
    def test_unadvertised_name_is_rejected(self, func_name):
        assert self._call(func_name, {'public', 'child.method'}) == []

    def test_names_match_inject_pywebview(self, monkeypatch):
        """The dispatch set is the one inject_pywebview advertises to Javascript."""
        window = _bridge_window(js_api=self.Api([]))
        window._functions = {}
        monkeypatch.setattr(
            util, 'load_js_files', lambda window, platform, restricted=False: ('', '%(functions)s')
        )

        util.inject_pywebview('test', window)

        # The finish script is the JS API guard line, then the advertised functions
        finish_script = window.gui.evaluate_js.call_args.args[0]
        advertised = {f['func'] for f in json.loads(finish_script.split('\n', 1)[1])}
        assert advertised == {'public', 'child.method'}
        assert window._js_api_names == advertised

    def test_state_update_cannot_reach_private_attributes(self):
        window = _bridge_window()
        handlers = window.state._State__event_handlers

        js_bridge_call(
            window,
            'pywebviewStateUpdate',
            {'key': '_State__event_handlers', 'value': None},
            'value-id',
            'document-token',
            TRUSTED_URL,
        )

        assert window.state._State__event_handlers is handlers
        assert window.state['_State__event_handlers'] is None

    @pytest.mark.parametrize(
        'url',
        ['http://example.com', 'HTTPS://example.com/a?b=c', 'mailto:someone@example.com'],
    )
    def test_external_url_is_opened(self, monkeypatch, url):
        opened = Mock()
        monkeypatch.setattr(util.webbrowser, 'open', opened)
        util.open_external_url(url)
        opened.assert_called_once_with(url, 0, True)

    @pytest.mark.parametrize(
        'url',
        [
            'file:///C:/Users/Public/run.bat',
            'FILE:///etc/passwd',
            'ms-settings:privacy',
            'javascript:alert(1)',
            'C:\\Windows\\System32\\calc.exe',
            '/usr/bin/xterm',
            '',
        ],
    )
    def test_non_web_url_is_not_opened(self, monkeypatch, url):
        opened = Mock()
        monkeypatch.setattr(util.webbrowser, 'open', opened)
        util.open_external_url(url)
        opened.assert_not_called()

    @pytest.mark.parametrize(
        'url, origin',
        [
            ('HTTPS://Example.COM:443/path?q=1', 'https://example.com'),
            ('http://127.0.0.1:8080/index.html', 'http://127.0.0.1:8080'),
            ('http://[::1]:8080/', 'http://[::1]:8080'),
            ('http://[0:0:0:0:0:0:0:1]:8080/', 'http://[::1]:8080'),
            ('http://127.1:8080/', 'http://127.0.0.1:8080'),
            ('http://2130706433/', 'http://127.0.0.1'),
            ('http://example.com:0/', 'http://example.com:0'),
            ('https://bücher.example/path', 'https://xn--bcher-kva.example'),
            ('https://faß.example/', 'invalid:'),
            ('https://xn--fa-hia.example/', 'https://xn--fa-hia.example'),
            ('file:///home/user/index.html', 'file:///home/user/index.html'),
            ('file:///home/app/../user/', 'file:///home/user/'),
            ('file:///home/user name/', 'file:///home/user%20name/'),
            ('about:blank', 'about:blank'),
            ('data:text/html,hi', 'data:text/html,hi'),
            (None, 'invalid:'),
            ('http://example.com:bad/', 'invalid:'),
        ],
    )
    def test_js_api_origin(self, url, origin):
        assert util.js_api_origin(url) == origin

    def test_js_api_allowed_origins(self, monkeypatch):
        window = SimpleNamespace(_js_api_origins={'http://127.0.0.1:8080'})
        settings = {'ALLOWED_ORIGINS': ['https://Example.com/']}
        monkeypatch.setattr(util.webview, 'settings', settings)

        assert util.is_js_api_allowed(window, 'http://127.0.0.1:8080/page.html')
        assert util.is_js_api_allowed(window, 'https://example.com/app')
        assert not util.is_js_api_allowed(window, 'http://127.0.0.1:9090/')
        assert not util.is_js_api_allowed(window, 'https://www.example.com/')
        assert not util.is_js_api_allowed(window, 'file:///etc/passwd')

        settings['ALLOWED_ORIGINS'] = ['*']
        assert util.is_js_api_allowed(window, 'https://anything.example/')
        assert util.js_api_guard(window) == 'true'

    def test_html_trust_is_document_specific(self):
        window = webview.create_window('HTML')
        window._allow_js_api_on(None)
        window._allow_js_api_on('file:///app/index.html')
        window._allow_js_api_on('data:text/html,owned')

        assert util.is_js_api_allowed(window, 'about:blank')
        assert util.is_js_api_allowed(window, 'file:///app/index.html#section')
        assert util.is_js_api_allowed(window, 'data:text/html,owned')
        assert not util.is_js_api_allowed(window, 'about:srcdoc')
        assert not util.is_js_api_allowed(window, 'file:///app/untrusted.html')
        assert not util.is_js_api_allowed(window, 'data:text/html,untrusted')
        assert not util.is_js_api_allowed(window, None)

    def test_ambiguous_unicode_origin_never_authorizes_another_host(self, monkeypatch):
        window = SimpleNamespace(_js_api_origins=set())
        monkeypatch.setitem(util.webview.settings, 'ALLOWED_ORIGINS', ['https://faß.example'])

        assert not util.is_js_api_allowed(window, 'https://fass.example/')
        assert not util.is_js_api_allowed(window, 'https://faß.example/')
        assert 'invalid:' not in util.js_api_guard(window)

    def test_html_base_uri_origin_is_trusted(self):
        window = webview.create_window('HTML')
        window.gui = Mock()
        window.events.shown.set()

        window.load_html('<html></html>', 'https://base.example/app/')

        assert util.is_js_api_allowed(window, 'https://base.example/app/')

    def test_explicit_blank_document_survives_navigation_invalidation(self):
        window = webview.create_window('Blank')
        window._allow_js_api_on('about:blank')
        window._invalidate_js_api()

        assert not util.is_local_url('about:blank')
        assert util.is_js_api_allowed(window, 'about:blank')

    @pytest.mark.parametrize(
        'url, granted',
        [
            ('https://example.com/app', True),
            ('http://127.0.0.1:42001/index.html', True),
            ('http://localhost:5173/', True),
            ('http://[::1]:8000/', True),
            ('http://example.com/app', False),
            ('http://192.168.1.10:8000/', False),
        ],
    )
    def test_python_loaded_origin_is_granted_unless_plain_remote_http(self, url, granted):
        window = webview.create_window('Auto trust')
        window._allow_js_api_on(url)

        assert util.is_js_api_allowed(window, url) == granted

    def test_listed_plain_http_origin_is_allowed(self, monkeypatch):
        window = webview.create_window('Auto trust')
        monkeypatch.setitem(util.webview.settings, 'ALLOWED_ORIGINS', ['http://example.com'])
        window._allow_js_api_on('http://example.com/app')

        assert util.is_js_api_allowed(window, 'http://example.com/app')

    def test_window_move_from_a_page(self):
        window = webview.create_window('Move', frameless=True)
        window.gui = Mock()
        window.events.shown.set()
        window.gui.get_screens.return_value = [
            SimpleNamespace(width=1920, height=1080),
            SimpleNamespace(width=1280, height=1024),
        ]

        def move(param):
            window.gui.move.reset_mock()
            js_bridge_call(window, 'pywebviewMoveWindow', param, 'move', 'not-the-token', None)
            return window.gui.move.call_args.args[:2] if window.gui.move.called else None

        # Accepted without a token, from any page
        assert move([10, -20]) == (10, -20)
        # Kept within the total extent of the screens, which also stops overflowing values
        assert move([1e12, -1e12]) == (3200, -2104)
        assert move(['x', {}]) is None
        assert move([1]) is None

        window.frameless = False
        assert move([10, 20]) is None

    def test_stopping_a_window_server_revokes_its_origin(self, monkeypatch):
        monkeypatch.setitem(webview.settings, 'ALLOWED_ORIGINS', ['http://127.0.0.1:1'])
        window = webview.create_window('Server')
        other = webview.create_window('Other')
        server = SimpleNamespace(address='http://127.0.0.1:50123/', stop=Mock())
        origin = util.js_api_origin(server.address)
        window._server = server
        window._js_api_origins.add(origin)
        other._js_api_origins.add(origin)

        window._stop_server()

        server.stop.assert_called_once()
        assert window._server is None
        assert not util.is_js_api_allowed(window, server.address)
        assert not util.is_js_api_allowed(other, server.address)
        assert util.is_js_api_allowed(other, 'http://127.0.0.1:1/')

    def test_restricted_page_gets_pywebview_without_tokens_or_state(self):
        window = webview.create_window('Restricted')
        window.state.secret = 'value'
        window._js_api_token = 'document-token'

        script, _ = util.load_js_files(window, 'edgechromium', restricted=True)
        assert util._TOKEN not in script
        assert 'secret' not in script
        assert 'window.pywebview = {' in script

        script, _ = util.load_js_files(window, 'edgechromium')
        assert util._TOKEN in script
        assert 'secret' in script

    @pytest.mark.parametrize('func_name', ['pywebviewEventHandler', 'pywebviewAsyncCallback'])
    def test_dom_calls_are_accepted_from_any_origin(self, func_name):
        window = webview.create_window('DOM')
        window._js_api_token = 'document-token'
        handled = threading.Event()
        window.dom._elements['node'] = SimpleNamespace(
            _event_listeners={'handler': ('click', lambda event: handled.set())}
        )
        window._callbacks['value-id'] = lambda value: handled.set()

        param = {'event': {'type': 'click'}, 'nodeId': 'node', 'handlerId': 'handler'}
        if func_name == 'pywebviewAsyncCallback':
            param = '"result"'
        js_bridge_call(
            window, func_name, param, 'value-id', 'document-token', 'https://untrusted.example/'
        )
        assert handled.wait(2)

    def test_drop_paths_reach_every_drop_listener(self, monkeypatch):
        from webview.dom import _dnd_state

        monkeypatch.setitem(
            _dnd_state, 'paths', [('a.txt', '/left/a.txt'), ('a.txt', '/right/a.txt')]
        )
        monkeypatch.setitem(_dnd_state, 'dropped', None)
        window = webview.create_window('DOM')
        window._js_api_token = 'document-token'
        received = []
        handled = threading.Semaphore(0)

        def handler(event):
            received.append([f.get('pywebviewFullPath') for f in event['dataTransfer']['files']])
            handled.release()

        window.dom._elements['node'] = SimpleNamespace(
            _event_listeners={'first': ('drop', handler), 'second': ('drop', handler)}
        )
        for handler_id in ('first', 'second'):
            files = [{'name': 'a.txt'}, {'name': 'a.txt'}]
            event = {'type': 'drop', 'timeStamp': 1.5, 'dataTransfer': {'files': files}}
            param = {'event': event, 'nodeId': 'node', 'handlerId': handler_id}
            js_bridge_call(
                window, 'pywebviewEventHandler', param, 'id', 'document-token', 'https://a.example/'
            )
            assert handled.acquire(timeout=2)

        assert received == [['/left/a.txt', '/right/a.txt']] * 2
        assert _dnd_state['paths'] == []

        # a later drop does not reuse the paths of this one
        event = {'type': 'drop', 'timeStamp': 9.5, 'dataTransfer': {'files': [{'name': 'a.txt'}]}}
        param = {'event': event, 'nodeId': 'node', 'handlerId': 'first'}
        js_bridge_call(
            window, 'pywebviewEventHandler', param, 'id', 'document-token', 'https://a.example/'
        )
        assert handled.acquire(timeout=2)
        assert received[-1] == [None]

        # nor does a drop with the same timestamp in another document
        monkeypatch.setitem(_dnd_state, 'paths', [('a.txt', '/left/a.txt')])
        event = {'type': 'drop', 'timeStamp': 3.0, 'dataTransfer': {'files': [{'name': 'a.txt'}]}}
        param = {'event': dict(event), 'nodeId': 'node', 'handlerId': 'first'}
        js_bridge_call(
            window, 'pywebviewEventHandler', param, 'id', 'document-token', 'https://a.example/'
        )
        assert handled.acquire(timeout=2)
        window._js_api_token = 'other-document'
        event['dataTransfer'] = {'files': [{'name': 'a.txt'}]}
        param = {'event': event, 'nodeId': 'node', 'handlerId': 'first'}
        js_bridge_call(
            window, 'pywebviewEventHandler', param, 'id', 'other-document', 'https://a.example/'
        )
        assert handled.acquire(timeout=2)
        assert received[-2:] == [['/left/a.txt'], [None]]

    @pytest.mark.parametrize('func_name', ['target', 'pywebviewStateUpdate'])
    def test_api_and_state_calls_need_an_allowed_origin(self, func_name):
        window = webview.create_window('DOM')
        window._js_api_token = 'document-token'
        window._functions['target'] = Mock()

        js_bridge_call(
            window,
            func_name,
            {'key': 'secret', 'value': 1},
            'value-id',
            'document-token',
            'https://untrusted.example/',
        )
        window._functions['target'].assert_not_called()
        assert 'secret' not in window.state

    @pytest.mark.parametrize('js_api, warned', [(None, False), (object(), True)])
    def test_restricted_page_warns_only_if_window_has_an_api(self, caplog, js_api, warned):
        caplog.set_level(logging.DEBUG, logger='pywebview')
        window = webview.create_window('Restricted', js_api=js_api)
        window.run_js = Mock()

        util.inject_pywebview('gtkwebkit2', window, 'https://www.example.com/')

        records = [r for r in caplog.records if 'are not available on' in r.getMessage()]
        assert len(records) == 1
        assert (records[0].levelno == logging.WARNING) == warned

    def test_trust_holds_for_the_document_until_navigation(self, monkeypatch):
        url = TRUSTED_URL
        window = _bridge_window(url, restricted=False)
        monkeypatch.setitem(util.webview.settings, 'ALLOWED_ORIGINS', [])
        assert _send(window, url)

        # Restricted when injected: allowing the origin later changes nothing for it
        window = _bridge_window(url, restricted=True)
        monkeypatch.setitem(util.webview.settings, 'ALLOWED_ORIGINS', ['https://trusted.example'])
        assert not _send(window, url)

        # A navigation resets the decision until the next injection
        window = _bridge_window(url, restricted=False)
        window._invalidate_js_api()
        window._js_api_token = 'document-token'
        assert not _send(window, url)

    def test_protected_window_methods_are_not_callable_from_js(self, monkeypatch, caplog):
        url = TRUSTED_URL
        window = _bridge_window(url, restricted=False)
        window.events.shown.set()
        window._js_api = SimpleNamespace(window=window)
        window._functions = {}
        monkeypatch.setattr(
            util, 'load_js_files', lambda window, platform, restricted=False: ('', '%(functions)s')
        )
        caplog.set_level(logging.WARNING, logger='pywebview')
        util.inject_pywebview('test', window)
        util.inject_pywebview('test', window)

        warnings = [r.getMessage() for r in caplog.records if 'is protected' in r.getMessage()]
        protected = ('load_url', 'load_html', 'expose', 'evaluate_js', 'run_js', 'get_cookies')
        assert sorted(w.split()[0] for w in warnings) == sorted(f'window.{n}' for n in protected)

        # Injection issued a new token and forgot the document; restore an authorized one
        window._js_api_token = 'document-token'
        window._js_api_restricted = False
        window._js_api_document_url = url
        window._functions['target'] = Mock(return_value='ok')
        js_bridge_call(window, 'target', [], 'value-id', 'document-token', url)
        window._functions['target'].assert_called_once()  # the bridge accepts this document

        scripts = window.gui.evaluate_js.call_count  # pywebview's own scripts go through it too
        for name in protected:
            assert f'window.{name}' not in window._js_api_names
            js_bridge_call(window, f'window.{name}', ['/'], 'value-id', 'document-token', url)
            with pytest.raises(SecurityException):
                window.expose(getattr(window, name))

        window.gui.load_url.assert_not_called()
        window.gui.load_html.assert_not_called()
        assert window.gui.evaluate_js.call_count == scripts
        window.gui.get_cookies.assert_not_called()
        assert 'window.minimize' in window._js_api_names

    def test_load_url_stays_within_the_served_folder(self, monkeypatch, tmp_path):
        root = tmp_path / 'public'
        window = webview.create_window('Files')
        window.gui = Mock()
        window.events.shown.set()
        window._server = SimpleNamespace(
            address='http://127.0.0.1:1/',
            running=True,
            serves_files=True,
            root_path=str(root),
            common_path=str(root),
        )
        start_server = Mock()
        monkeypatch.setattr(webview.http, 'start_server', start_server)

        def loaded_url():  # relpath() puts backslashes in the URL on Windows
            return window.gui.load_url.call_args[0][0].replace('\\', '/')

        window.load_url(str(root / 'page.html'))
        assert loaded_url() == 'http://127.0.0.1:1/page.html'

        with pytest.raises(SecurityException):
            window.load_url(str(tmp_path / 'private' / 'page.html'))
        assert window.gui.load_url.call_count == 1
        start_server.assert_not_called()

        # A server without a root, as start(http_server=True) starts, gets a file server
        window._server.root_path = None
        server = SimpleNamespace(address='http://127.0.0.1:2/', common_path=str(tmp_path))
        start_server.return_value = (server.address, server.common_path, server)
        window.load_url(str(tmp_path / 'private' / 'page.html'))
        assert loaded_url() == 'http://127.0.0.1:2/private/page.html'

    @staticmethod
    def _reply(window):
        """Return the value passed to the JS callback in the last script sent to the page."""
        script = window.gui.evaluate_js.call_args[0][0]
        return json.loads(re.search(r'\]\((\{.*\})\) \}$', script).group(1))

    @pytest.mark.parametrize('value', ['it\'s a "quote" \\ \n \u2028', {'a': [1, None]}, 42])
    def test_result_reply_is_json(self, value):
        window = _bridge_window()
        window._functions['target'].return_value = value
        assert _send(window, TRUSTED_URL)

        reply = self._reply(window)
        assert 'isError' not in reply
        assert json.loads(reply['value']) == value

    def test_error_reply_is_json(self):
        window = _bridge_window()
        window._functions['target'].side_effect = ValueError("it's broken")
        assert _send(window, TRUSTED_URL)

        reply = self._reply(window)
        assert reply['isError'] is True
        error = json.loads(reply['value'])
        assert (error['name'], error['message']) == ('ValueError', "it's broken")
        assert 'Traceback' in error['stack']

    def test_missing_nested_api_attribute_is_reported(self, caplog):
        assert self._call('child.missing', {'child.missing'}) == []
        assert 'Function child.missing() does not exist' in caplog.text

    def test_state_delete_from_the_page_is_not_sent_back(self, caplog):
        url = TRUSTED_URL
        window = _bridge_window(url, restricted=False)
        window._run_js_api_js = Mock()
        js_bridge_call(
            window, 'pywebviewStateUpdate', {'key': 'a', 'value': 1}, 'id', 'document-token', url
        )
        assert window.state == {'a': 1}

        js_bridge_call(window, 'pywebviewStateDelete', 'a', 'id', 'document-token', url)
        js_bridge_call(window, 'pywebviewStateDelete', 'missing', 'id', 'document-token', url)

        assert window.state == {}
        window._run_js_api_js.assert_not_called()
        assert not [r for r in caplog.records if r.levelno >= logging.ERROR]

    @pytest.mark.parametrize('restricted', [True, False])
    def test_expose_warns_on_a_restricted_document(self, caplog, restricted):
        caplog.set_level(logging.WARNING, logger='pywebview')
        window = _bridge_window('https://www.example.com/', restricted)
        window.gui.reset_mock()
        window.events.loaded.set()

        def late():
            pass

        window.expose(late)

        warned = 'Exposed functions are not available on https://www.example.com/' in caplog.text
        assert warned == restricted
        assert window.gui.evaluate_js.called != restricted

    def test_https_with_ignored_ssl_errors_warns(self, monkeypatch, caplog):
        # CI runs with PYWEBVIEW_LOG=error, which would drop the warning
        caplog.set_level(logging.WARNING, logger='pywebview')
        window = webview.create_window('Auto trust')
        monkeypatch.setitem(util.webview.settings, 'IGNORE_SSL_ERRORS', True)
        window._allow_js_api_on('https://example.com/app')

        assert util.is_js_api_allowed(window, 'https://example.com/app')
        assert 'IGNORE_SSL_ERRORS' in caplog.text


class TestLocalTlsCert:
    """ssl=True trusts the local HTTP server's own certificate, not every certificate."""

    @staticmethod
    def _pem(der):
        import base64
        import textwrap

        body = '\n'.join(textwrap.wrap(base64.b64encode(der).decode(), 64))
        return f'-----BEGIN CERTIFICATE-----\n{body}\n-----END CERTIFICATE-----\n'

    def test_pem_to_der(self):
        der = bytes(range(200))
        assert util.pem_to_der(self._pem(der)) == der
        assert util.pem_to_der(self._pem(der).replace('\n', '\r\n')) == der
        assert util.pem_to_der('no certificate here') is None
        assert util.pem_to_der('-----BEGIN CERTIFICATE-----\n!!\n-----END CERTIFICATE-----') is None

    def test_only_the_local_certificate_is_accepted(self, monkeypatch, tmp_path):
        monkeypatch.setattr(util, '_local_tls_cert', None)
        local, other = b'local certificate', b'some other certificate'
        assert not util.is_local_tls_cert(local)
        assert not util.has_local_tls_cert()

        certfile = tmp_path / 'cert.pem'
        certfile.write_text(self._pem(local))
        util.set_local_tls_cert(str(certfile))

        assert util.is_local_tls_cert(local)
        assert not util.is_local_tls_cert(other)
        assert not util.is_local_tls_cert(None)
        assert util.has_local_tls_cert()

        # start() without ssl=True forgets it
        util.set_local_tls_cert(None)
        assert not util.has_local_tls_cert()
        assert not util.is_local_tls_cert(local)


class TestWindowApiCall:
    """Window methods wait for a window event before they call the backend."""

    def test_raises_without_a_gui(self):
        window = webview.create_window('No GUI')
        window.events.shown.set()
        with pytest.raises(WebViewException, match='GUI is not initialized'):
            window.show()

    def test_raises_when_the_event_times_out(self, monkeypatch):
        window = webview.create_window('Timeout')
        window.gui = Mock()
        monkeypatch.setattr(window.events.shown, 'wait', lambda timeout=None: False)
        with pytest.raises(WebViewException, match='failed to start'):
            window.show()
        window.gui.show.assert_not_called()

    @pytest.mark.parametrize('method, args', [('get_cookies', ()), ('evaluate_js', ('1',))])
    def test_page_methods_fail_in_a_blocking_handler_before_load(self, method, args):
        window = webview.create_window('Blocking')
        window.gui = Mock()
        errors = []

        def before_show():
            try:
                getattr(window, method)(*args)
            except WebViewException as e:
                errors.append(str(e))

        window.events.before_show += before_show
        window.events.before_show.set()

        assert errors == [f'{method}() cannot be called before the page has loaded']
        window.gui.get_cookies.assert_not_called()
        window.gui.evaluate_js.assert_not_called()

    def test_other_methods_call_the_backend_in_a_blocking_handler(self):
        window = webview.create_window('Blocking')
        window.gui = Mock()
        window.events.before_show += lambda: window.get_current_url()
        window.events.before_show.set()
        window.gui.get_current_url.assert_called_once_with(window.uid)

    @pytest.mark.parametrize('renderer', ['android-webkit', 'cocoa'])
    def test_evaluate_js_script_ends_with_its_value(self, renderer):
        """
        Android returns the value of a function call, other backends the value of the last
        statement, where a return statement would be a syntax error.
        """
        window = webview.create_window('Evaluate')
        window.gui = Mock(renderer=renderer)
        window.events._pywebviewready.set()

        window.evaluate_js('1 + 1')

        script = window.gui.evaluate_js.call_args[0][0].strip()
        if renderer == 'android-webkit':
            assert re.fullmatch(
                r'\(function\(\) \{.*return pywebview\.stringify\(value\);+\s*\}\)\(\)',
                script,
                re.S,
            )
        else:
            assert 'return' not in script
            assert re.search(r'\bpywebview\.stringify\(value\);+$', script)


class TestLoadUrlServer:
    """load_url() reuses the window's server only for local URLs that it can serve."""

    @staticmethod
    def _window(monkeypatch, **server):
        window = webview.create_window('Server')
        window.gui = Mock()
        window.events.shown.set()
        window._server = SimpleNamespace(address='http://127.0.0.1:1/', stop=Mock(), **server)
        start_server = Mock()
        new_server = SimpleNamespace(address='http://127.0.0.1:2/', common_path='.')
        start_server.return_value = (new_server.address, new_server.common_path, new_server)
        monkeypatch.setattr(webview.http, 'start_server', start_server)
        return window, start_server

    def test_app_server_serves_local_paths_as_routes(self, monkeypatch):
        window, start_server = self._window(
            monkeypatch, running=True, serves_files=False, root_path='/app', common_path='.'
        )
        window.load_url('route/page.html')

        start_server.assert_not_called()
        assert window.gui.load_url.call_args[0][0] == 'http://127.0.0.1:1/route/page.html'

    def test_stopped_server_is_replaced(self, monkeypatch, tmp_path):
        window, start_server = self._window(
            monkeypatch, running=False, serves_files=True, root_path=str(tmp_path)
        )
        old_server = window._server
        window.load_url(str(tmp_path / 'page.html'))

        old_server.stop.assert_called_once()
        start_server.assert_called_once()
        assert window.gui.load_url.call_args[0][0].startswith('http://127.0.0.1:2/')

    def test_path_on_another_drive_is_outside_the_root(self, monkeypatch, tmp_path):
        window, start_server = self._window(
            monkeypatch, running=True, serves_files=True, root_path=str(tmp_path)
        )

        def commonpath(paths):
            raise ValueError("Paths don't have the same drive")

        monkeypatch.setattr(os.path, 'commonpath', commonpath)
        with pytest.raises(SecurityException):
            window.load_url(str(tmp_path / 'page.html'))
        window.gui.load_url.assert_not_called()
        start_server.assert_not_called()


class TestState:
    @staticmethod
    def _window(monkeypatch, loaded=True):
        window = webview.create_window('State')
        monkeypatch.setattr(window, '_run_js_api_js', Mock())
        if loaded:
            window.events.loaded.set()
        changes: Queue = Queue()
        window.state += lambda type, key, value: changes.put((type, key, value))
        return window, changes

    def test_change_is_sent_to_the_page_once(self, monkeypatch):
        window, changes = self._window(monkeypatch)
        window.state.a = 1
        assert changes.get(timeout=2) == ('change', 'a', 1)
        assert '"__pywebviewHaltUpdate__a"' in window._run_js_api_js.call_args[0][0]

        window._run_js_api_js.reset_mock()
        window.state.a = 1  # unchanged
        window.state['b'] = 2
        assert changes.get(timeout=2) == ('change', 'b', 2)
        assert window._run_js_api_js.call_count == 1

    def test_change_before_load_is_sent_on_load(self, monkeypatch):
        window, changes = self._window(monkeypatch, loaded=False)
        window.state.a = 1
        window._run_js_api_js.assert_not_called()
        with pytest.raises(Empty):
            changes.get(timeout=0.2)

        window.events.loaded.set()
        assert changes.get(timeout=2) == ('change', 'a', 1)
        window._run_js_api_js.assert_called_once()

    def test_delete(self, monkeypatch):
        window, changes = self._window(monkeypatch)
        window.state.update(a=1, b=2)  # dict.update stores without sending

        del window.state.a
        assert changes.get(timeout=2) == ('delete', 'a', 1)
        script = window._run_js_api_js.call_args[0][0]
        assert script == 'delete window.pywebview.state["__pywebviewHaltUpdate__a"]'

        del window.state['b']
        assert changes.get(timeout=2) == ('delete', 'b', 2)

        with pytest.raises(AttributeError):
            del window.state.a
        with pytest.raises(KeyError):
            del window.state['b']

    def test_removed_handler_is_not_called(self, monkeypatch):
        window, changes = self._window(monkeypatch)
        removed = Mock()
        window.state += removed
        window.state -= removed
        window.state.a = 1
        assert changes.get(timeout=2) == ('change', 'a', 1)
        removed.assert_not_called()


class TestEvent:
    def test_handlers_are_added_and_removed(self, caplog):
        from webview.event import Event

        caplog.set_level(logging.WARNING, logger='pywebview')

        event = Event(None, True, 'blocking')
        handler = Mock(return_value=None)
        event += handler
        assert len(event) == 1
        event -= handler
        event -= handler
        assert len(event) == 0
        assert 'not found' in caplog.text

        async def coroutine():
            pass

        with pytest.raises(TypeError):
            event += coroutine

    def test_blocking_event_returns_whether_a_handler_cancelled(self):
        from webview.event import Event

        window = object()
        event = Event(window, True, 'blocking')
        received = []
        event += lambda: None
        event += lambda window: received.append(window)
        assert event.set() is False
        assert received == [window]

        event += lambda: False
        assert event.set() is True
        assert event.is_set()


class TestGuilib:
    """Backend selection, without importing the backends."""

    @pytest.fixture
    def guilib(self, monkeypatch):
        # webview.guilib is the selected backend, so import the module by its full name
        guilib = importlib.import_module('webview.guilib')
        tried: list[str] = []
        failing: dict[str, Exception] = {}

        def import_backend(name):
            tried.append(name)
            if name in failing:
                raise failing[name]
            return SimpleNamespace(__name__=name, setup_app=Mock())

        monkeypatch.setattr(guilib, '_import_backend', import_backend)
        monkeypatch.setattr(guilib, 'guilib', None)
        monkeypatch.delenv('PYWEBVIEW_GUI', raising=False)
        monkeypatch.delenv('KDE_FULL_SESSION', raising=False)
        monkeypatch.delattr(sys, 'getandroidapilevel', raising=False)
        return SimpleNamespace(module=guilib, tried=tried, failing=failing)

    @pytest.mark.parametrize(
        'system, env, kde, order',
        [
            ('Darwin', None, False, ['cocoa', 'qt']),
            ('Darwin', 'QT', False, ['qt', 'cocoa']),
            ('Darwin', 'unknown', False, ['cocoa', 'qt']),
            ('Darwin', 'cef', False, ['cocoa', 'qt']),
            ('Linux', None, False, ['gtk', 'qt']),
            ('Linux', None, True, ['qt', 'gtk']),
            ('OpenBSD', 'gtk', True, ['gtk', 'qt']),
            ('Windows', None, False, ['winforms', 'winui3']),
            ('Windows', 'qt', False, ['qt', 'winforms', 'winui3']),
            ('Windows', 'winui3', False, ['winui3']),
            ('Windows', 'edgechromium', False, ['winforms']),
        ],
    )
    def test_backend_order(self, guilib, monkeypatch, caplog, system, env, kde, order):
        caplog.set_level(logging.WARNING, logger='pywebview')
        monkeypatch.setattr(guilib.module.platform, 'system', lambda: system)
        if env:
            monkeypatch.setenv('PYWEBVIEW_GUI', env)
        if kde:
            monkeypatch.setenv('KDE_FULL_SESSION', 'true')
        guilib.failing.update(dict.fromkeys(guilib.module._BACKENDS, ImportError('missing')))

        with pytest.raises(WebViewException):
            guilib.module.initialize()

        assert guilib.tried == order
        assert ('support has been removed' in caplog.text) == (env == 'cef')

    def test_forced_gui_argument_overrides_the_environment(self, guilib, monkeypatch):
        monkeypatch.setattr(guilib.module.platform, 'system', lambda: 'Linux')
        monkeypatch.setenv('PYWEBVIEW_GUI', 'gtk')
        assert guilib.module.initialize('qt').__name__ == 'qt'
        assert guilib.module.forced_gui_ == 'qt'

    def test_falls_back_to_the_next_backend(self, guilib, monkeypatch, caplog):
        monkeypatch.setattr(guilib.module.platform, 'system', lambda: 'Darwin')
        guilib.failing['cocoa'] = ImportError('no PyObjC')

        module = guilib.module.initialize()

        assert module.__name__ == 'qt'
        assert guilib.module.guilib is module
        module.setup_app.assert_called_once()
        assert 'PyObjC cannot be loaded' in caplog.text

    def test_only_the_expected_errors_fall_back(self, guilib, monkeypatch):
        monkeypatch.setattr(guilib.module.platform, 'system', lambda: 'Windows')
        guilib.failing['winforms'] = RuntimeError('pythonnet')
        assert guilib.module.initialize().__name__ == 'winui3'

        guilib.failing['winui3'] = RuntimeError('unexpected')
        with pytest.raises(RuntimeError, match='unexpected'):
            guilib.module.initialize('winui3')

    def test_unsupported_platform(self, guilib, monkeypatch):
        monkeypatch.setattr(guilib.module.platform, 'system', lambda: 'Plan9')
        with pytest.raises(WebViewException, match='Unsupported platform'):
            guilib.module.initialize()
        assert guilib.tried == []

    def test_android(self, guilib, monkeypatch):
        monkeypatch.setattr(guilib.module.platform, 'system', lambda: 'Linux')
        monkeypatch.setattr(sys, 'getandroidapilevel', lambda: 34, raising=False)
        assert guilib.module.initialize().__name__ == 'android'
        assert guilib.tried == ['android']

    def test_names_import_their_backend(self, monkeypatch):
        import webview.platforms

        guilib = importlib.import_module('webview.guilib')
        for name in guilib._BACKENDS:
            # A stand-in module, as the backend's native library is not installed everywhere
            module = ModuleType(f'webview.platforms.{name}')
            monkeypatch.setitem(sys.modules, module.__name__, module)
            monkeypatch.setattr(webview.platforms, name, module, raising=False)
            assert guilib._import_backend(name) is module


class TestHelpers:
    def test_immutable_dict(self):
        settings = util.ImmutableDict({'a': 1}, b=2)
        settings['a'] = 3
        assert dict(settings) == {'a': 3, 'b': 2}
        with pytest.raises(KeyError):
            settings['c'] = 1
        with pytest.raises(KeyError):
            del settings['a']

    @pytest.mark.parametrize(
        'url, local',
        [
            ('index.html', True),
            ('/abs/index.html', True),
            ('http://example.com', False),
            ('https://example.com', False),
            ('file:///index.html', False),
            ('about:blank#top', False),
            ('', False),
            (None, False),
            (lambda environ, start_response: [], False),
        ],
    )
    def test_is_local_url(self, url, local):
        assert util.is_local_url(url) is local

    def test_sort_js_files(self):
        files = ['js/finish.js', 'js/state.js', 'js/a.js', 'js/api.js', 'js/lib/b.js']
        assert util.sort_js_files(files) == [
            'js/api.js',
            'js/state.js',
            'js/finish.js',
            'js/a.js',
            'js/lib/b.js',
        ]

    @pytest.mark.parametrize(
        'content, expected',
        [
            ('<html><head></head></html>', '<html><head>BASE</head></html>'),
            ('<html><head lang="en"></head></html>', '<html><head lang="en">BASE</head></html>'),
            ('<html lang="en"><body></body></html>', '<html lang="en">BASE<body></body></html>'),
            ('<body>text</body>', 'BASE<body>text</body>'),
            ('<header>text</header>', 'BASE<header>text</header>'),
            ('text', 'BASEtext'),
            ('<head><base href="other"></head>', '<head><base href="other"></head>'),
        ],
    )
    def test_inject_base_uri(self, content, expected):
        base = '<base href="file:///app/">'
        assert util.inject_base_uri(content, 'file:///app/') == expected.replace('BASE', base)

    @pytest.mark.parametrize('freezer', ['pyinstaller', 'cx_freeze'])
    def test_interop_dll_path_in_a_frozen_app(self, monkeypatch, tmp_path, freezer):
        monkeypatch.delenv('PYTHONNET_RUNTIME', raising=False)
        dll = tmp_path / 'Test.Interop.dll'
        dll.write_bytes(b'')
        monkeypatch.delattr(sys, '_MEIPASS', raising=False)
        monkeypatch.delattr(sys, 'frozen', raising=False)
        if freezer == 'pyinstaller':
            monkeypatch.setattr(sys, '_MEIPASS', str(tmp_path), raising=False)
        else:
            monkeypatch.setattr(sys, 'frozen', True, raising=False)
            monkeypatch.setattr(sys, 'executable', str(tmp_path / 'app.exe'))

        assert util.interop_dll_path('Test.Interop.dll') == str(dll)

    def test_interop_dll_path_not_found(self, monkeypatch):
        monkeypatch.delattr(sys, '_MEIPASS', raising=False)
        monkeypatch.delattr(sys, 'frozen', raising=False)
        with pytest.raises(FileNotFoundError, match='Missing.dll'):
            util.interop_dll_path('Missing.dll')
