import pytest

from webview.util import parse_file_type


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
