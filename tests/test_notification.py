import subprocess
import sys

import pytest

import webview.notification as notification
from webview.errors import WebViewException


class TestNotifyDispatch:
    def test_unsupported_platform(self, monkeypatch):
        monkeypatch.setattr(sys, 'platform', 'freebsd13')
        with pytest.raises(WebViewException):
            notification.notify('Title', 'Message')


class TestEscapeApplescript:
    def test_plain_text_unchanged(self):
        assert notification._escape_applescript('hello world') == 'hello world'

    def test_escapes_double_quotes(self):
        assert notification._escape_applescript('say "hi"') == 'say \\"hi\\"'

    def test_escapes_backslashes(self):
        assert notification._escape_applescript('a\\b') == 'a\\\\b'


class TestNotifyLinux:
    def test_falls_back_to_notify_send_when_libnotify_unavailable(self, monkeypatch):
        # Force the `gi`/Notify import path to fail so we exercise the
        # notify-send subprocess fallback deterministically, regardless of
        # whether gi/libnotify happen to be installed in this environment.
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == 'gi':
                raise ImportError('mocked: gi not installed')
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, '__import__', fake_import)
        monkeypatch.setattr(notification.shutil, 'which', lambda _cmd: '/usr/bin/notify-send')

        calls = []

        def fake_run(cmd, check, capture_output):
            calls.append(cmd)

        monkeypatch.setattr(notification.subprocess, 'run', fake_run)
        monkeypatch.setattr(sys, 'platform', 'linux')

        notification.notify('Title', 'Message', app_name='pytest')

        assert len(calls) == 1
        assert calls[0][0] == '/usr/bin/notify-send'
        assert calls[0][1:] == ['Title', 'Message']

    def test_raises_when_no_backend_available(self, monkeypatch):
        monkeypatch.setattr(notification.shutil, 'which', lambda _cmd: None)
        monkeypatch.setattr(sys, 'platform', 'linux')

        # Simulate `gi`/libnotify being unimportable too.
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == 'gi':
                raise ImportError('mocked: gi not installed')
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, '__import__', fake_import)

        with pytest.raises(WebViewException, match='libnotify'):
            notification.notify('Title', 'Message')


class TestNotifyMacos:
    def test_calls_osascript_with_escaped_args(self, monkeypatch):
        calls = []

        def fake_run(cmd, check, capture_output):
            calls.append(cmd)

        monkeypatch.setattr(notification.subprocess, 'run', fake_run)
        monkeypatch.setattr(sys, 'platform', 'darwin')

        notification.notify('My "App"', 'Hello')

        assert len(calls) == 1
        assert calls[0][0] == 'osascript'
        assert calls[0][1] == '-e'
        assert 'My \\"App\\"' in calls[0][2]

    def test_raises_on_failure(self, monkeypatch):
        def fake_run(cmd, check, capture_output):
            raise subprocess.CalledProcessError(1, cmd)

        monkeypatch.setattr(notification.subprocess, 'run', fake_run)
        monkeypatch.setattr(sys, 'platform', 'darwin')

        with pytest.raises(WebViewException):
            notification.notify('Title', 'Message')
