import threading
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest

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
    """Tests that js_bridge_call enforces the session token before dispatching a call."""

    def _make_window(self, called_event):
        def target():
            called_event.set()
            return 'ok'

        window = MagicMock()
        window._functions = {'target': target}
        return window

    def test_valid_token_invokes_function(self):
        """A call carrying the correct token is dispatched to the exposed function"""
        called = threading.Event()
        window = self._make_window(called)
        js_bridge_call(window, 'target', [], 'value_id', _TOKEN)
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

        assert is_js_bridge_token_valid(window, _TOKEN)
        assert not is_js_bridge_token_valid(window, 'not-the-token')


class TestBridgeDispatch:
    """Tests that js_bridge_call dispatches only the js_api names advertised to the page."""

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
            self.child = TestBridgeDispatch.Child(called)

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
        js_bridge_call(window, func_name, [], 'value_id', _TOKEN)
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
        handlers = window.state._State__event_handlers

        js_bridge_call(
            window,
            'pywebviewStateUpdate',
            {'key': '_State__event_handlers', 'value': None},
            'value_id',
            _TOKEN,
        )

        assert window.state._State__event_handlers is handlers
        assert window.state['_State__event_handlers'] is None
