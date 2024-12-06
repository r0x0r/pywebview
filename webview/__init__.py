"""
pywebview is a lightweight cross-platform wrapper around a webview component that allows to display HTML content in its
own dedicated window. Works on Windows, OS X and Linux and compatible with Python 2 and 3.

(C) 2014-2019 Roman Sirokov and contributors
Licensed under BSD license

http://github.com/r0x0r/pywebview/
"""

from __future__ import annotations

import datetime
import logging
import os
import re
import tempfile
import threading
from collections.abc import Iterable, Mapping
from typing import Any, Callable
from uuid import uuid4

from proxy_tools import module_property

import webview.http as http
from webview.errors import JavascriptException, WebViewException
from webview.event import Event
from webview.guilib import initialize, GUIType
from webview.localization import original_localization
from webview.menu import Menu
from webview.screen import Screen
from webview.util import (ImmutableDict, _TOKEN, abspath, base_uri, escape_line_breaks, escape_string,
                          is_app, is_local_url, parse_file_type)
from webview.window import Window

__all__ = (
    # Stuff that's here
    'active_window',
    'start',
    'create_window',
    'token',
    'renderer',
    'screens',
    'settings',
    # From event
    'Event',
    # from util    '
    'JavascriptException',
    'WebViewException',
    # from screen
    'Screen',
    # from window
    'Window',
)

logger = logging.getLogger('pywebview')
_handler = logging.StreamHandler()
_formatter = logging.Formatter('[pywebview] %(message)s')
_handler.setFormatter(_formatter)
logger.addHandler(_handler)

log_level = logging._nameToLevel[os.environ.get('PYWEBVIEW_LOG', 'info').upper()]
logger.setLevel(log_level)

OPEN_DIALOG = 10
FOLDER_DIALOG = 20
SAVE_DIALOG = 30

DRAG_REGION_SELECTOR = '.pywebview-drag-region'
DEFAULT_HTTP_PORT = 42001

settings = ImmutableDict({
    'ALLOW_DOWNLOADS': False,
    'ALLOW_FILE_URLS': True,
    'OPEN_EXTERNAL_LINKS_IN_BROWSER': True,
    'OPEN_DEVTOOLS_IN_DEBUG': True,
    'REMOTE_DEBUGGING_PORT': None,
    'IGNORE_SSL_ERRORS': False,
})

_state = ImmutableDict({
    'debug': False,
    'storage_path': None,
    'private_mode': True,
    'user_agent': None,
    'http_server': False,
    'ssl': False,
    'icon': None
})

guilib = None

token = _TOKEN
windows: list[Window] = []
menus: list[Menu] = []
renderer: str | None = None


def start(
    func: Callable[..., None] | None = None,
    args: Iterable[Any] | None = None,
    localization: dict[str, str] = {},
    gui: GUIType | None = None,
    debug: bool = False,
    http_server: bool = False,
    http_port: int | None = None,
    user_agent: str | None = None,
    private_mode: bool = True,
    storage_path: str | None = None,
    menu: list[Menu] = [],
    server: type[http.ServerType] = http.BottleServer,
    server_args: dict[Any, Any] = {},
    ssl: bool = False,
    icon: str | None = None,
):
    """
    Start a GUI loop and display previously created windows. This function must
    be called from a main thread.

    :param func: Function to invoke upon starting the GUI loop.
    :param args: Function arguments. Can be either a single value or a tuple of
        values.
    :param localization: A dictionary with localized strings. Default strings
        and their keys are defined in localization.py.
    :param gui: Force a specific GUI. Allowed values are ``cef``, ``qt``,
        ``gtk``, ``mshtml`` or ``edgechromium`` depending on a platform.
    :param debug: Enable debug mode. Default is False.
    :param http_server: Enable built-in HTTP server. If enabled, local files
        will be served using a local HTTP server on a random port. For each
        window, a separate HTTP server is spawned. This option is ignored for
        non-local URLs.
    :param user_agent: Change user agent string.
    :param private_mode: Enable private mode. In private mode, cookies and local storage are not preserved.
           Default is True.
    :param storage_path: Custom location for cookies and other website data
    :param menu: List of menus to be included in the app menu
    :param server: Server class. Defaults to BottleServer
    :param server_args: Dictionary of arguments to pass through to the server instantiation
    :param ssl: Enable SSL for local HTTP server. Default is False.
    :param icon: Path to the icon file. Supported only on GTK/QT.
    """
    global guilib, renderer

    def _create_children(other_windows):
        if not windows[0].events.shown.wait(10):
            raise WebViewException('Main window failed to load')

        for window in other_windows:
            guilib.create_window(window)

    _state['debug'] = debug
    _state['user_agent'] = user_agent
    _state['http_server'] = http_server
    _state['private_mode'] = private_mode

    if icon:
        _state['icon'] = abspath(icon)

    if storage_path:
        __set_storage_path(storage_path)

    if debug:
        logger.setLevel(logging.DEBUG)

    if _state['storage_path'] and _state['private_mode'] and not os.path.exists(_state['storage_path']):
        os.makedirs(_state['storage_path'])

    original_localization.update(localization)

    if threading.current_thread().name != 'MainThread':
        raise WebViewException('pywebview must be run on a main thread.')

    if len(windows) == 0:
        raise WebViewException('You must create a window first before calling this function.')

    guilib = initialize(gui)
    renderer = guilib.renderer

    if ssl:
        # generate SSL certs and tell the windows to use them
        keyfile, certfile = __generate_ssl_cert()
        server_args['keyfile'] = keyfile
        server_args['certfile'] = certfile
        _state['ssl'] = True
    else:
        keyfile, certfile = None, None

    urls = [w.original_url for w in windows]
    has_local_urls = not not [w.original_url for w in windows if is_local_url(w.original_url)]
    # start the global server if it's not running and we need it
    if (http.global_server is None) and (http_server or has_local_urls):
        if not _state['private_mode'] and not http_port:
            http_port = DEFAULT_HTTP_PORT
        *_, server = http.start_global_server(
            http_port=http_port, urls=urls, server=server, **server_args
        )

    for window in windows:
        window._initialize(guilib)

    if ssl:
        for window in windows:
            window.gui.add_tls_cert(certfile)

    if len(windows) > 1:
        thread = threading.Thread(target=_create_children, args=(windows[1:],))
        thread.start()

    if func:
        if args is not None:
            if not hasattr(args, '__iter__'):
                args = (args,)
            thread = threading.Thread(target=func, args=args)
        else:
            thread = threading.Thread(target=func)
        thread.start()

    if menu:
        guilib.set_app_menu(menu)
    guilib.create_window(windows[0])
    # keyfile is deleted by the ServerAdapter right after wrap_socket()
    if certfile:
        os.unlink(certfile)


def create_window(
    title: str,
    url: str | None = None,
    html: str | None = None,
    js_api: Any = None,
    width: int = 800,
    height: int = 600,
    x: int | None = None,
    y: int | None = None,
    screen: Screen = None,
    resizable: bool = True,
    fullscreen: bool = False,
    min_size: tuple[int, int] = (200, 100),
    hidden: bool = False,
    frameless: bool = False,
    easy_drag: bool = True,
    shadow: bool = True,
    focus: bool = True,
    minimized: bool = False,
    maximized: bool = False,
    on_top: bool = False,
    confirm_close: bool = False,
    background_color: str = '#FFFFFF',
    transparent: bool = False,
    text_select: bool = False,
    zoomable: bool = False,
    draggable: bool = False,
    vibrancy: bool = False,
    localization: Mapping[str, str] | None = None,
    server: type[http.ServerType] = http.BottleServer,
    http_port: int | None = None,
    server_args: http.ServerArgs = {},
) -> Window:
    """
    Create a web view window using a native GUI. The execution blocks after this function is invoked, so other
    program logic must be executed in a separate thread.
    :param title: Window title
    :param url: URL to load
    :param html: HTML content to load
    :param width: window width. Default is 800px
    :param height: window height. Default is 600px
    :param screen: Screen to display the window on.
    :param resizable: True if window can be resized, False otherwise. Default is True
    :param fullscreen: True if start in fullscreen mode. Default is False
    :param min_size: a (width, height) tuple that specifies a minimum window size. Default is 200x100
    :param hidden: Whether the window should be hidden.
    :param frameless: Whether the window should have a frame.
    :param easy_drag: Easy window drag mode when window is frameless.
    :param shadow: Whether the window should have a frame border (shadows and Windows rounded edges).
    :param focus: Whether to activate the window when user opens it. Window can be controlled with mouse but keyboard input will go to another (active) window and not this one.
    :param minimized: Display window minimized
    :param maximized: Display window maximized
    :param on_top: Keep window above other windows (required OS: Windows)
    :param confirm_close: Display a window close confirmation dialog. Default is False
    :param background_color: Background color as a hex string that is displayed before the content of webview is loaded. Default is white.
    :param text_select: Allow text selection on page. Default is False.
    :param transparent: Don't draw window background.
    :param server: Server class. Defaults to BottleServer
    :param server_args: Dictionary of arguments to pass through to the server instantiation
    :return: window object.
    """

    valid_color = r'^#(?:[0-9a-fA-F]{3}){1,2}$'
    if not re.match(valid_color, background_color):
        raise ValueError('{0} is not a valid hex triplet color'.format(background_color))

    uid = 'master' if len(windows) == 0 else 'child_' + uuid4().hex[:8]

    window = Window(
        uid,
        title,
        url,
        html,
        width,
        height,
        x,
        y,
        resizable,
        fullscreen,
        min_size,
        hidden,
        frameless,
        easy_drag,
        shadow,
        focus,
        minimized,
        maximized,
        on_top,
        confirm_close,
        background_color,
        js_api,
        text_select,
        transparent,
        zoomable,
        draggable,
        vibrancy,
        localization,
        server=server,
        http_port=http_port,
        server_args=server_args,
        screen=screen,
    )

    windows.append(window)

    # This immediately creates the window only if `start` has already been called
    if threading.current_thread().name != 'MainThread' and guilib:
        if is_app(url) or is_local_url(url) and not server.is_running:
            url_prefix, common_path, server = http.start_server([url], server=server, **server_args)
        else:
            url_prefix, common_path, server = None, None, None

        window._initialize(gui=guilib, server=server)
        guilib.create_window(window)

    return window


def __generate_ssl_cert():
    # https://cryptography.io/en/latest/x509/tutorial/#creating-a-self-signed-certificate
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    with tempfile.NamedTemporaryFile(prefix='keyfile_', suffix='.pem', delete=False) as f:
        keyfile = f.name
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        key_pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),  # BestAvailableEncryption(b"passphrase"),
        )
        f.write(key_pem)

    with tempfile.NamedTemporaryFile(prefix='certfile_', suffix='.pem', delete=False) as f:
        certfile = f.name
        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, 'US'),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, 'California'),
                x509.NameAttribute(NameOID.LOCALITY_NAME, 'San Francisco'),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'pywebview'),
                x509.NameAttribute(NameOID.COMMON_NAME, '127.0.0.1'),
            ]
        )
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.utcnow())
            .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
            .add_extension(
                x509.SubjectAlternativeName([x509.DNSName('localhost')]),
                critical=False,
            )
            .sign(key, hashes.SHA256(), backend=default_backend())
        )
        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        f.write(cert_pem)

    return keyfile, certfile


def __set_storage_path(storage_path):
    e = WebViewException(f'Storage path {storage_path} is not writable')

    if not os.path.exists(storage_path):
        try:
            os.makedirs(storage_path)
        except OSError:
            raise e
    if not os.access(storage_path, os.W_OK):
        raise e

    _state['storage_path'] = storage_path


def active_window() -> Window | None:
    """
    Get the active window

    :return: window object or None
    """
    if guilib:
        return guilib.get_active_window()
    return None


@module_property
def screens() -> list[Screen]:
    global renderer, guilib

    if not guilib:
        guilib = initialize()
        renderer = guilib.renderer

    screens = guilib.get_screens()
    return screens

