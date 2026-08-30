import sys

import pytest

import webview.keyring as keyring
from webview.errors import WebViewException


class TestKeyringDispatch:
    """Tests for the platform dispatch in webview.keyring"""

    def test_unsupported_platform_set(self, monkeypatch):
        monkeypatch.setattr(sys, 'platform', 'freebsd13')
        with pytest.raises(WebViewException):
            keyring.set_password('service', 'user', 'pass')

    def test_unsupported_platform_get(self, monkeypatch):
        monkeypatch.setattr(sys, 'platform', 'freebsd13')
        with pytest.raises(WebViewException):
            keyring.get_password('service', 'user')

    def test_unsupported_platform_delete(self, monkeypatch):
        monkeypatch.setattr(sys, 'platform', 'freebsd13')
        with pytest.raises(WebViewException):
            keyring.delete_password('service', 'user')


class TestLinuxFileFallback:
    """
    Tests for the encrypted-file fallback used on Linux when no Secret
    Service implementation is reachable. Exercises the private
    _linux_*_file functions directly so this runs regardless of whether a
    real Secret Service / D-Bus session is available in the test environment.
    """

    @pytest.fixture(autouse=True)
    def _isolate_fallback_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(keyring, '_linux_fallback_dir', lambda: str(tmp_path))
        yield

    def test_roundtrip(self):
        pytest.importorskip('cryptography')
        keyring._linux_set_password_file('myapp', 'alice', 's3cr3t')
        assert keyring._linux_get_password_file('myapp', 'alice') == 's3cr3t'

    def test_missing_credential_returns_none(self):
        pytest.importorskip('cryptography')
        assert keyring._linux_get_password_file('myapp', 'nobody') is None

    def test_delete_then_missing(self):
        pytest.importorskip('cryptography')
        keyring._linux_set_password_file('myapp', 'bob', 'hunter2')
        keyring._linux_delete_password_file('myapp', 'bob')
        assert keyring._linux_get_password_file('myapp', 'bob') is None

    def test_delete_nonexistent_is_noop(self):
        # Should not raise even though nothing was ever stored
        keyring._linux_delete_password_file('myapp', 'ghost')

    def test_raises_clear_error_without_cryptography(self, monkeypatch):
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == 'cryptography.fernet' or name.startswith('cryptography'):
                raise ImportError('mocked: cryptography not installed')
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, '__import__', fake_import)
        with pytest.raises(WebViewException, match='cryptography'):
            keyring._linux_set_password_file('myapp', 'alice', 'secret')
