import threading
from unittest.mock import MagicMock

import pytest

from webview.util import (
    _TOKEN,
    create_cookie,
    is_js_bridge_token_valid,
    js_bridge_call,
    parse_file_type,
)


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
