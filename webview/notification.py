"""
(C) 2014-2019 Roman Sirokov and contributors
Licensed under BSD license

http://github.com/r0x0r/pywebview/

Cross-platform native OS notification support.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import threading
import time

from webview.errors import WebViewException


def notify(title: str, message: str, app_name: str = 'pywebview') -> None:
    """
    Display a native OS notification.

    :param title: Notification title
    :param message: Notification body text
    :param app_name: Application name shown in the notification. Only used on Windows and Linux.
    """
    if sys.platform == 'darwin':
        _notify_macos(title, message)
    elif sys.platform == 'win32':
        _notify_windows(title, message, app_name)
    elif sys.platform.startswith('linux'):
        _notify_linux(title, message, app_name)
    else:
        raise WebViewException(f'Notifications are not supported on platform {sys.platform!r}')


def _escape_applescript(value: str) -> str:
    return value.replace('\\', '\\\\').replace('"', '\\"')


def _notify_macos(title: str, message: str) -> None:
    script = (
        f'display notification "{_escape_applescript(message)}" '
        f'with title "{_escape_applescript(title)}"'
    )
    try:
        subprocess.run(['osascript', '-e', script], check=True, capture_output=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        raise WebViewException(f'Failed to display notification: {e}') from e


def _notify_windows(title: str, message: str, app_name: str) -> None:
    try:
        import clr

        clr.AddReference('System.Windows.Forms')
        clr.AddReference('System.Drawing')
        import System.Windows.Forms as WinForms
        from System.Drawing import SystemIcons
    except ImportError as e:
        raise WebViewException('Notifications require pythonnet on Windows.') from e

    icon = WinForms.NotifyIcon()
    icon.Icon = SystemIcons.Information
    icon.Visible = True
    icon.Text = app_name[:63]  # NotifyIcon.Text is limited to 63 characters
    icon.BalloonTipTitle = title
    icon.BalloonTipText = message
    icon.ShowBalloonTip(5000)

    def _cleanup() -> None:
        time.sleep(6)
        icon.Visible = False
        icon.Dispose()

    threading.Thread(target=_cleanup, daemon=True).start()


def _notify_linux(title: str, message: str, app_name: str) -> None:
    try:
        import gi

        gi.require_version('Notify', '0.7')
        from gi.repository import Notify

        if not Notify.is_initted():
            Notify.init(app_name)
        Notify.Notification.new(title, message).show()
        return
    except (ImportError, ValueError):
        pass

    notify_send = shutil.which('notify-send')
    if not notify_send:
        raise WebViewException(
            'Notifications require libnotify. Install the "gir1.2-notify-0.7" system package '
            '(or equivalent for your distribution), or ensure the notify-send command is available.'
        )
    try:
        subprocess.run([notify_send, title, message], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        raise WebViewException(f'Failed to display notification: {e}') from e
