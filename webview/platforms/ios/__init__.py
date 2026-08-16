"""iOS WKWebView backend.

The iOS application host owns UIKit and WebKit.  The embedded Python runtime
exposes the small ``pywebview_ios`` native module used here; keeping that
module boundary narrow allows the rest of pywebview to remain platform
independent.
"""

from __future__ import annotations

import logging

from webview.errors import WebViewException

logger = logging.getLogger('pywebview2')
renderer = 'ios'

try:
    import pywebview_ios as native
except ImportError as e:  # pragma: no cover - only executed by an iOS app
    raise ImportError('The pywebview_ios native module is required for the iOS backend.') from e


def setup_app():
    native.setup_app()


def create_window(window):
    native.create_window(window.uid, window.title)
    if window.real_url:
        load_url(window.real_url, window.uid)
    elif window.html:
        load_html(window.html, '', window.uid)


def destroy_window(uid):
    native.destroy_window(uid)


def load_url(url, uid):
    native.load_url(url, uid)


def load_html(content, base_uri, uid):
    native.load_html(content, base_uri, uid)


def evaluate_js(script, uid, parse_json=True):
    return native.evaluate_js(script, uid, parse_json)


def get_current_url(uid):
    return native.get_current_url(uid)


def get_cookies(uid):
    return native.get_cookies(uid)


def clear_cookies(uid):
    native.clear_cookies(uid)


def create_file_dialog(*_):
    raise WebViewException('File dialogs are not implemented for the iOS backend yet.')


def create_confirmation_dialog(title, message, uid):
    return native.create_confirmation_dialog(title, message, uid)


def get_screens():
    return native.get_screens()


def get_size(uid):
    return native.get_size(uid)


def get_position(uid):
    return (0, 0)


def set_title(title, uid):
    native.set_title(title, uid)


def show(uid):
    native.show(uid)


def hide(uid):
    native.hide(uid)


def toggle_fullscreen(uid):
    native.toggle_fullscreen(uid)


def set_on_top(_, __):
    logger.warning('Always-on-top mode is not supported on iOS')


def resize(_, __, ___, ____):
    logger.warning('Window resizing is not supported on iOS')


def move(_, __, ___):
    logger.warning('Window movement is not supported on iOS')


def minimize(uid):
    native.hide(uid)


def maximize(_):
    logger.warning('Window maximization is not supported on iOS')


def restore(uid):
    native.show(uid)


def add_tls_cert(_):
    logger.warning('Custom TLS certificates are not supported by the iOS backend yet')
