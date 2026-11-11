import json
import logging
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest

import webview
from webview import util
from webview.errors import WebViewException
from webview.util import (
    _TOKEN,
    create_cookie,
    is_js_bridge_token_valid,
    js_bridge_call,
    parse_file_type,
)


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


class TestParseFileType:
    """Tests for the parse_file_type function"""

    def test_simple_single_extension(self):
        """Test basic single extension format"""
        description, extensions = parse_file_type('Images (*.png)')
        assert description == 'Images'
        assert extensions == '*.png'

    def test_simple_multiple_extensions(self):
        """Test basic multiple extensions format"""
        description, extensions = parse_file_type('Images (*.png;*.jpg;*.gif)')
        assert description == 'Images'
        assert extensions == '*.png;*.jpg;*.gif'

    def test_double_dot_extensions_first_position(self):
        """Test extensions with multiple dots in first position"""
        description, extensions = parse_file_type('Archives (*.tar.gz;*.zip)')
        assert description == 'Archives'
        assert extensions == '*.tar.gz;*.zip'

    def test_double_dot_extensions_later_position(self):
        """Test extensions with multiple dots in later positions (the original bug)"""
        description, extensions = parse_file_type('Archives (*.zip;*.tar.gz)')
        assert description == 'Archives'
        assert extensions == '*.zip;*.tar.gz'

    def test_multiple_double_dot_extensions(self):
        """Test multiple extensions all with multiple dots"""
        description, extensions = parse_file_type('Archives (*.tar.gz;*.tar.bz2;*.tar.xz)')
        assert description == 'Archives'
        assert extensions == '*.tar.gz;*.tar.bz2;*.tar.xz'

    def test_mixed_extension_formats(self):
        """Test mix of single and multi-dot extensions"""
        description, extensions = parse_file_type('Mixed (*.txt;*.log.gz;*.csv;*.backup.old)')
        assert description == 'Mixed'
        assert extensions == '*.txt;*.log.gz;*.csv;*.backup.old'

    def test_asterisk_wildcard(self):
        """Test asterisk wildcard extension"""
        description, extensions = parse_file_type('All files (*.*)')
        assert description == 'All files'
        assert extensions == '*.*'

    def test_bare_asterisk(self):
        """Test bare asterisk extension"""
        description, extensions = parse_file_type('All files (*)')
        assert description == 'All files'
        assert extensions == '*'

    def test_description_with_spaces(self):
        """Test description containing multiple words"""
        description, extensions = parse_file_type('JPEG Image Files (*.jpg;*.jpeg)')
        assert description == 'JPEG Image Files'
        assert extensions == '*.jpg;*.jpeg'

    def test_description_with_numbers(self):
        """Test description containing numbers"""
        description, extensions = parse_file_type('MP3 Audio Files (*.mp3)')
        assert description == 'MP3 Audio Files'
        assert extensions == '*.mp3'

    def test_complex_real_world_example(self):
        """Test complex real-world file filter"""
        description, extensions = parse_file_type(
            'Data Files (*.idat;*.idat.gz;*.csv;*.tsv;*.json)'
        )
        assert description == 'Data Files'
        assert extensions == '*.idat;*.idat.gz;*.csv;*.tsv;*.json'

    def test_whitespace_in_description(self):
        """Test description with various whitespace"""
        description, extensions = parse_file_type('Text  Files (*.txt)')
        assert description == 'Text  Files'  # Whitespace should be preserved
        assert extensions == '*.txt'

    # Error cases
    def test_invalid_format_no_parentheses(self):
        """Test invalid format without parentheses"""
        with pytest.raises(ValueError, match='is not a valid file filter'):
            parse_file_type('Images *.png')

    def test_invalid_format_no_description(self):
        """Test invalid format without description"""
        with pytest.raises(ValueError, match='is not a valid file filter'):
            parse_file_type('(*.png)')

    def test_invalid_format_no_extensions(self):
        """Test invalid format without extensions"""
        with pytest.raises(ValueError, match='is not a valid file filter'):
            parse_file_type('Images ()')

    def test_invalid_format_no_asterisk(self):
        """Test invalid format without asterisk prefix"""
        with pytest.raises(ValueError, match='is not a valid file filter'):
            parse_file_type('Images (png;jpg)')

    def test_invalid_format_malformed_parentheses(self):
        """Test invalid format with malformed parentheses"""
        with pytest.raises(ValueError, match='is not a valid file filter'):
            parse_file_type('Images (*.png')

    def test_empty_string(self):
        """Test empty string input"""
        with pytest.raises(ValueError, match='is not a valid file filter'):
            parse_file_type('')

    def test_invalid_characters_in_description(self):
        """Test invalid characters in description (only word chars and spaces allowed)"""
        with pytest.raises(ValueError, match='is not a valid file filter'):
            parse_file_type('Images-Files (*.png)')

    def test_extension_without_dot(self):
        """Test extension without leading dot"""
        with pytest.raises(ValueError, match='is not a valid file filter'):
            parse_file_type('Images (*png)')

    def test_semicolon_without_asterisk(self):
        """Test semicolon separator without asterisk"""
        with pytest.raises(ValueError, match='is not a valid file filter'):
            parse_file_type('Images (*.png;.jpg)')

    # Edge cases that should work
    def test_single_character_extension(self):
        """Test single character extension"""
        description, extensions = parse_file_type('C Files (*.c)')
        assert description == 'C Files'
        assert extensions == '*.c'

    def test_very_long_extension(self):
        """Test very long extension"""
        description, extensions = parse_file_type('Files (*.verylongextension)')
        assert description == 'Files'
        assert extensions == '*.verylongextension'

    def test_triple_dot_extension(self):
        """Test extension with three dots"""
        description, extensions = parse_file_type('Backup (*.backup.old.gz)')
        assert description == 'Backup'
        assert extensions == '*.backup.old.gz'


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


class TestBridgeTokenValidation:
    """Tests that bridge calls require the current document's token and a native URL."""

    def _make_window(self, called_event):
        def target():
            called_event.set()
            return 'ok'

        window = MagicMock()
        window._functions = {'target': target}
        window._js_api_token = 'document-token'
        window._js_api_origins = {'https://trusted.example'}
        return window

    def test_valid_token_invokes_function(self):
        """A call carrying the correct token is dispatched to the exposed function"""
        called = threading.Event()
        window = self._make_window(called)
        js_bridge_call(
            window, 'target', [], 'value_id', window._js_api_token, 'https://trusted.example'
        )
        assert called.wait(2), 'Function was not called for a valid token'

    def test_invalid_token_rejects_call(self):
        """A call carrying a wrong token is rejected and the function is never invoked"""
        called = threading.Event()
        window = self._make_window(called)
        js_bridge_call(window, 'target', [], 'value_id', 'not-the-token')
        assert not called.wait(0.5), 'Function was called despite an invalid token'

    def test_internal_command_token_validation(self):
        window = MagicMock()
        window.gui.renderer = 'winui3'
        window._js_api_token = 'document-token'

        assert is_js_bridge_token_valid(window, window._js_api_token)
        assert not is_js_bridge_token_valid(window, 'not-the-token')
        assert not is_js_bridge_token_valid(window, _TOKEN)

    @pytest.mark.parametrize('source_url', [None, 'https://untrusted.example'])
    def test_missing_or_untrusted_native_url_is_rejected(self, source_url):
        called = threading.Event()
        window = self._make_window(called)
        js_bridge_call(window, 'target', [], 'value_id', window._js_api_token, source_url)
        assert not called.wait(0.1)

    def test_navigation_revokes_document_token(self):
        window = webview.create_window('Token', html='<html></html>')
        window._js_api_token = 'old-document'
        window._js_api_pending_html = False
        window._js_api_origins.add('about:blank')
        window._invalidate_js_api()
        assert not is_js_bridge_token_valid(window, 'old-document')
        assert not util.is_js_api_allowed(window, 'about:blank')

    def test_result_uses_native_execution_and_document_guard(self, monkeypatch):
        called = threading.Event()
        window = self._make_window(called)
        monkeypatch.setattr(util, 'Thread', lambda target: SimpleNamespace(start=target))

        js_bridge_call(
            window, 'target', [], 'value_id', window._js_api_token, 'https://trusted.example'
        )

        window.evaluate_js.assert_not_called()
        script = window.run_js.call_args.args[0]
        assert '._bridgeToken === "document-token"' in script
        assert 'https://trusted.example' in script

    def test_callback_id_is_a_quoted_property_key(self, monkeypatch):
        called = threading.Event()
        window = self._make_window(called)
        monkeypatch.setattr(util, 'Thread', lambda target: SimpleNamespace(start=target))
        value_id = '"]; } window.captured = "secret"; //'

        js_bridge_call(
            window, 'target', [], value_id, window._js_api_token, 'https://trusted.example'
        )

        script = window.run_js.call_args.args[0]
        assert f'_returnValuesCallbacks["target"][{json.dumps(value_id)}]' in script


class TestJsBridgeHardening:
    """What a page can reach through the JS bridge and external links."""

    class Child:
        def __init__(self, called):
            self._called = called

        def method(self):
            self._called.set('child.method')

        def _hidden(self):
            self._called.set('child._hidden')

    class Api:
        def __init__(self, called):
            self._called = called
            self.child = TestJsBridgeHardening.Child(called)

        def public(self):
            self._called.set('public')

        def _private(self):
            self._called.set('_private')

    class Recorder:
        def __init__(self):
            self.name = None
            self.event = threading.Event()

        def set(self, name):
            self.name = name
            self.event.set()

    def _call(self, func_name, advertised):
        called = self.Recorder()
        window = MagicMock()
        window._functions = {}
        window._js_api = self.Api(called)
        window._js_api_names = frozenset(advertised)
        window._js_api_token = 'document-token'
        window._js_api_origins = {'https://trusted.example'}
        js_bridge_call(
            window, func_name, [], 'value_id', window._js_api_token, 'https://trusted.example'
        )
        return called

    @pytest.mark.parametrize('func_name', ['public', 'child.method'])
    def test_advertised_name_is_dispatched(self, func_name):
        called = self._call(func_name, {'public', 'child.method'})
        assert called.event.wait(2)
        assert called.name == func_name

    @pytest.mark.parametrize(
        'func_name', ['_private', 'child._hidden', '_called.set', 'child', 'public.__call__']
    )
    def test_unadvertised_name_is_rejected(self, func_name):
        called = self._call(func_name, {'public', 'child.method'})
        assert not called.event.wait(0.5)

    def test_names_match_inject_pywebview(self, monkeypatch):
        """The dispatch set is the one inject_pywebview advertises to Javascript."""
        api = self.Api(self.Recorder())
        window = MagicMock()
        window._js_api = api
        window._functions = {}
        monkeypatch.setattr(util, 'load_js_files', lambda window, platform: ('', '%(functions)s'))
        monkeypatch.setattr(util, 'Thread', lambda target: SimpleNamespace(start=target))

        util.inject_pywebview('test', window)

        assert window._js_api_names == frozenset({'public', 'child.method'})

    def test_state_update_cannot_reach_private_attributes(self):
        from webview.state import State

        window = MagicMock()
        window.state = State(window)
        window._js_api_token = 'document-token'
        window._js_api_origins = {'https://trusted.example'}
        handlers = window.state._State__event_handlers

        js_bridge_call(
            window,
            'pywebviewStateUpdate',
            {'key': '_State__event_handlers', 'value': None},
            'value_id',
            window._js_api_token,
            'https://trusted.example',
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
        settings = {'JS_API_ALLOWED_ORIGINS': ['https://Example.com/']}
        monkeypatch.setattr(util.webview, 'settings', settings)

        assert util.is_js_api_allowed(window, 'http://127.0.0.1:8080/page.html')
        assert util.is_js_api_allowed(window, 'https://example.com/app')
        assert not util.is_js_api_allowed(window, 'http://127.0.0.1:9090/')
        assert not util.is_js_api_allowed(window, 'https://www.example.com/')
        assert not util.is_js_api_allowed(window, 'file:///etc/passwd')

        settings['JS_API_ALLOWED_ORIGINS'] = ['*']
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
        monkeypatch.setitem(
            util.webview.settings, 'JS_API_ALLOWED_ORIGINS', ['https://faß.example']
        )

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
        monkeypatch.setitem(util.webview.settings, 'JS_API_ALLOWED_ORIGINS', ['http://example.com'])
        window._allow_js_api_on('http://example.com/app')

        assert util.is_js_api_allowed(window, 'http://example.com/app')

    def test_window_move_from_a_page(self):
        window = MagicMock(frameless=True)
        window.gui.get_screens.return_value = [
            SimpleNamespace(width=1920, height=1080),
            SimpleNamespace(width=1280, height=1024),
        ]

        def move(param):
            window.move.reset_mock()
            js_bridge_call(window, 'pywebviewMoveWindow', param, 'move', 'not-the-token', None)
            return window.move.call_args.args if window.move.called else None

        # Accepted without a token, from any page
        assert move([10, -20]) == (10, -20)
        # Kept within the total extent of the screens, which also stops overflowing values
        assert move([1e12, -1e12]) == (3200, -2104)
        assert move(['x', {}]) is None
        assert move([1]) is None

        window.frameless = False
        assert move([10, 20]) is None

    def test_ui_script_carries_no_api_or_token(self):
        window = webview.create_window('UI')
        script = util.load_ui_js(window, 'edgechromium')

        assert "'True' === 'True'" in script
        assert util._TOKEN not in script
        assert 'window.pywebview =' not in script

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

        certfile = tmp_path / 'cert.pem'
        certfile.write_text(self._pem(local))
        util.set_local_tls_cert(str(certfile))

        assert util.is_local_tls_cert(local)
        assert not util.is_local_tls_cert(other)
        assert not util.is_local_tls_cert(None)
