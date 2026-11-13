"""
(C) 2014-2019 Roman Sirokov and contributors
Licensed under BSD license

http://github.com/r0x0r/pywebview/
"""

from __future__ import annotations

import asyncio
import base64
import hmac
import inspect
import ipaddress
import json
import logging
import os
import posixpath
import re
import socket
import sys
import sysconfig
import traceback
import urllib.parse
import webbrowser
from collections import UserDict
from collections.abc import Callable
from concurrent.futures import Future
from glob import escape as glob_escape
from glob import glob
from http.cookies import SimpleCookie
from threading import RLock, Thread
from typing import TYPE_CHECKING, Any, TypeGuard
from uuid import uuid4

import webview
from webview.dom import _dnd_state
from webview.errors import WebViewException

if TYPE_CHECKING:
    from webview.window import Window

_TOKEN = uuid4().hex
RUNTIME_CONFIG = 'pywebview-runtimeconfig.json'

DEFAULT_HTML = """
    <!doctype html>
    <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1.0, user-scalable=0">
        </head>
        <body></body>
    </html>
"""

logger = logging.getLogger('pywebview')


# The asyncio event loop that runs coroutines returned by JS API functions and event handlers.
# `owned` is True when pywebview created the loop itself and is responsible for closing it.
_async_lock = RLock()
_async_futures: set[Future[Any]] = set()
_async_state: dict[str, Any] = {
    'loop': None,
    'thread': None,
    'owned': False,
    'stopped': False,
}


def set_event_loop(loop: asyncio.AbstractEventLoop | None) -> None:
    """
    Set the event loop used to run coroutines. A loop that is not running is run in a background
    thread. With None, a loop is created on demand the first time a coroutine needs to run.
    """
    stop_event_loop()

    with _async_lock:
        _async_state.update(loop=loop, thread=None, owned=False, stopped=False)
        if loop is not None and not loop.is_running():
            _start_loop_thread(loop)


def _start_loop_thread(loop: asyncio.AbstractEventLoop) -> None:
    thread = Thread(target=loop.run_forever, name='pywebview-asyncio', daemon=True)
    thread.start()
    _async_state['thread'] = thread


def get_event_loop() -> asyncio.AbstractEventLoop:
    """Return the event loop for running coroutines, starting one if none is set."""
    with _async_lock:
        if _async_state['stopped']:
            raise WebViewException('Cannot run coroutines after the event loop has been stopped')

        loop = _async_state['loop']
        if loop is None or loop.is_closed():
            loop = asyncio.new_event_loop()
            _async_state.update(loop=loop, owned=True)
            _start_loop_thread(loop)
        return loop


def run_async(awaitable: Any) -> Any:
    """Run an awaitable on the event loop and block the calling thread until it completes."""

    async def _await():
        return await awaitable

    coroutine = _await()
    try:
        # Submit under the lifecycle lock so shutdown cancels every accepted coroutine.
        with _async_lock:
            loop = get_event_loop()
            try:
                running_loop = asyncio.get_running_loop()
            except RuntimeError:
                running_loop = None

            if running_loop is loop:
                raise WebViewException('Cannot block the event loop thread waiting for a coroutine')

            future = asyncio.run_coroutine_threadsafe(coroutine, loop)
            _async_futures.add(future)
    except Exception:
        coroutine.close()
        if inspect.iscoroutine(awaitable):
            awaitable.close()
        raise

    try:
        return future.result()
    finally:
        with _async_lock:
            _async_futures.discard(future)


def call_maybe_async(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Call a function, running the awaitable it returns (if any) on the event loop."""
    result = func(*args, **kwargs)
    if inspect.isawaitable(result):
        result = run_async(result)
    return result


def stop_event_loop() -> None:
    """Cancel callback submissions and close the event loop if pywebview created it."""
    with _async_lock:
        loop, thread, owned = _async_state['loop'], _async_state['thread'], _async_state['owned']
        _async_state.update(loop=None, thread=None, owned=False, stopped=True)
        futures = list(_async_futures)
        _async_futures.clear()

    async def _cancel_tasks():
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await loop.shutdown_asyncgens()

    close_loop = owned and loop is not None and not loop.is_closed()
    if close_loop:
        try:
            asyncio.run_coroutine_threadsafe(_cancel_tasks(), loop).result(5)
        except Exception:
            logger.exception('Error while cancelling pending coroutines')

    # Let owned-loop tasks finish cancellation cleanup before settling any remaining waiters.
    for future in futures:
        future.cancel()

    if not close_loop:
        return

    loop.call_soon_threadsafe(loop.stop)
    if thread is not None:
        thread.join(5)
    if not loop.is_running():
        loop.close()


def configure_coreclr() -> None:
    """Set pythonnet's coreclr environment before importing clr."""
    runtimeconfig = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib', RUNTIME_CONFIG)
    os.environ.setdefault('PYTHONNET_CORECLR_RUNTIME_CONFIG', runtimeconfig)

    # An x64 Python on Windows ARM64 must use the side-by-side x64 dotnet install.
    if sys.platform == 'win32' and sysconfig.get_platform() == 'win-amd64':
        x64_root = os.path.join(
            os.environ.get('ProgramFiles', r'C:\Program Files'), 'dotnet', 'x64'
        )
        if os.path.isdir(x64_root):
            os.environ.setdefault('DOTNET_ROOT', x64_root)
            os.environ.setdefault('DOTNET_ROOT_X64', x64_root)


def _load(runtime: str) -> None:
    os.environ['PYTHONNET_RUNTIME'] = runtime
    try:
        import clr  # noqa: F401
    except BaseException:
        for module in ('clr', 'pythonnet'):
            sys.modules.pop(module, None)
        raise


def select_runtime(load: Callable[[str], None] = _load) -> str:
    """Load pythonnet, preferring coreclr and falling back to netfx."""
    pythonnet = sys.modules.get('pythonnet')
    runtime_info = pythonnet.get_runtime_info() if pythonnet is not None else None
    if runtime_info is not None:
        chosen = runtime_info.kind.lower()
        if chosen == '.net framework':
            chosen = 'netfx'
        if chosen not in ('coreclr', 'netfx', 'mono'):
            raise RuntimeError(f'Unsupported initialized pythonnet runtime: {runtime_info.kind}')
        os.environ['PYTHONNET_RUNTIME'] = chosen
        load(chosen)
        logger.debug('Using existing .NET framework: %s', chosen)
        return chosen

    chosen = os.environ.get('PYTHONNET_RUNTIME')
    if chosen:
        if chosen == 'default':
            chosen = 'netfx' if sys.platform == 'win32' else 'mono'
            os.environ['PYTHONNET_RUNTIME'] = chosen
        if chosen == 'coreclr':
            configure_coreclr()
        load(chosen)
        logger.debug('Using .NET framework: %s', chosen)
        return chosen

    configure_coreclr()
    os.environ['PYTHONNET_RUNTIME'] = 'coreclr'
    try:
        load('coreclr')
    except Exception as coreclr_error:
        logger.debug('coreclr unavailable, falling back to netfx: %s', coreclr_error)
        os.environ['PYTHONNET_RUNTIME'] = 'netfx'
        try:
            load('netfx')
        except Exception as netfx_error:
            raise RuntimeError(
                f'Could not load pythonnet on either runtime. '
                f'coreclr: {coreclr_error}. netfx: {netfx_error}.'
            ) from coreclr_error
        logger.debug('Using .NET framework: netfx')
        return 'netfx'

    logger.debug('Using .NET framework: coreclr')
    return 'coreclr'


class ImmutableDict(UserDict):
    """ "
    A dictionary that does not allow adding new keys or deleting existing ones.
    Only existing keys can be modified.
    """

    def __init__(self, initial_data: dict[Any, Any] | None = None, **kwargs: Any) -> None:
        self.data = {}
        if initial_data:
            self.data.update(initial_data)
        if kwargs:
            self.data.update(kwargs)

    def __setitem__(self, key: Any, value: Any) -> None:
        if key not in self.data:
            raise KeyError(f"Cannot add new key '{key}'. Only existing keys can be modified.")
        super().__setitem__(key, value)

    def __delitem__(self, key: Any) -> None:
        raise KeyError('Deleting keys is not allowed.')


def is_app(url: str | Callable[..., Any] | None) -> TypeGuard[Callable[..., Any]]:
    """Returns true if 'url' is a WSGI app."""
    return callable(url)


def is_local_url(url: str | Callable[..., Any] | None) -> TypeGuard[str]:
    if is_app(url) or not url or not isinstance(url, str):
        return False
    return not (
        url.startswith('http://')
        or url.startswith('https://')
        or url.startswith('file://')
        or urllib.parse.urldefrag(url)[0] == 'about:blank'
    )


def needs_server(urls: list[str]) -> bool:
    return bool([url for url in urls if (is_app(url) or is_local_url(url))])


def get_app_root() -> str:
    """
    Gets the file root of the application.
    """

    if hasattr(sys, '_MEIPASS'):  # Pyinstaller
        return sys._MEIPASS

    resource_path = os.getenv('RESOURCEPATH')  # py2app
    if resource_path:
        return resource_path

    if getattr(sys, 'frozen', False):  # cx_freeze
        return os.path.dirname(sys.executable)

    # Before the pytest branch: the suite also runs on-device under pytest,
    # where there is no sibling tests/ directory and the pytest branch would
    # return a path that does not exist.
    if hasattr(sys, 'getandroidapilevel'):
        return os.getenv('ANDROID_APP_PATH') or ''

    if 'pytest' in sys.modules and os.getenv('PYWEBVIEW_TEST'):
        return os.path.join(os.path.dirname(__file__), '..', 'tests')

    return os.path.dirname(os.path.realpath(sys.argv[0]))


def is_test_mode():
    """During the test suite (PYWEBVIEW_TEST) windows should not steal system focus."""
    return bool(os.environ.get('PYWEBVIEW_TEST'))


def abspath(path: str) -> str:
    """
    Make path absolute, using the application root
    """
    path = os.fspath(path)
    if not os.path.isabs(path):
        path = os.path.join(get_app_root(), path)
    return os.path.normpath(path)


def base_uri(relative_path: str = '') -> str:
    """Get absolute path to resource, works for dev and for PyInstaller"""
    base_path = get_app_root()
    if not os.path.exists(base_path):
        raise ValueError(f'Path {base_path} does not exist')

    return f'file://{os.path.join(base_path, relative_path)}'


def create_cookie(input_: dict[Any, Any] | str) -> SimpleCookie:
    if isinstance(input_, dict):
        cookie = SimpleCookie()
        name = input_['name']
        cookie[name] = input_['value']
        cookie[name]['path'] = input_['path']
        cookie[name]['domain'] = input_['domain']
        # A Morsel treats only '' as "omit this attribute" - passing None
        # through (as backends do for a session cookie with no expiry, e.g.
        # winui3.py's _format_cookie_expiry) makes SimpleCookie.output()
        # render the literal string "expires=None" instead of leaving the
        # attribute out. Check `is None` specifically, not truthiness: 0 is
        # a legitimate expiry (the Unix epoch, used to expire a cookie
        # immediately) and must not be normalized away like None is.
        cookie[name]['expires'] = '' if input_['expires'] is None else input_['expires']
        cookie[name]['secure'] = input_['secure']
        cookie[name]['httponly'] = input_['httponly']
        # Same None-vs-'' issue as expires above: several backends (e.g.
        # winui3.py, edgechromium.py) can't distinguish "SameSite absent"
        # from "SameSite=None" in the underlying platform API and report
        # both as None here - passing that through renders the literal
        # string "SameSite=None" in the output. Omit the attribute instead
        # of asserting a policy this backend can't actually confirm.
        same_site = input_.get('samesite')
        cookie[name]['samesite'] = '' if same_site is None else same_site

        return cookie

    if isinstance(input_, str):
        return SimpleCookie(input_)

    raise WebViewException('Unknown input to create_cookie')


def parse_file_type(file_type: str) -> tuple[str, str]:
    """
    :param file_type: file type string 'description (*.file_extension1;*.file_extension2)' as required by file filter in create_file_dialog
    :return: (description, file extensions) tuple
    """
    valid_file_filter = r'^([\w ]+)\((\*(?:\.(?:\w+|\*))*(?:;\*(?:\.(?:\w+|\*))*)*)\)$'
    match = re.search(valid_file_filter, file_type)

    if match:
        return match.group(1).rstrip(), match.group(2)
    raise ValueError(f'{file_type} is not a valid file filter')


def js_api_origin(url: str | None) -> str:
    """
    Return an HTTP(S) origin, or an exact document URL for opaque/local documents.
    """
    if not url:
        return 'invalid:'

    parts = urllib.parse.urlsplit(url)
    scheme = parts.scheme.lower()
    if scheme == 'file':
        path = posixpath.normpath(urllib.parse.unquote(parts.path))
        if parts.path.endswith('/') and not path.endswith('/'):
            path += '/'
        path = urllib.parse.quote(path, safe="/:@!$&'()*+,;=-._~")
        return urllib.parse.urlunsplit(('file', parts.netloc, path, parts.query, ''))
    if scheme not in ('http', 'https'):
        return urllib.parse.urldefrag(url)[0]

    try:
        port = parts.port
    except ValueError:
        return 'invalid:'

    try:
        hostname = parts.hostname or ''
        host = hostname.encode('idna').decode('ascii')
        if not hostname.isascii() and host.encode('ascii').decode('idna') != hostname:
            logger.warning('Unsupported Unicode hostname %s; use its Punycode form', hostname)
            return 'invalid:'
    except UnicodeError:
        return 'invalid:'
    if ':' in host:
        if '%' in host:
            return 'invalid:'
        host = f'[{ipaddress.IPv6Address(host).compressed}]'
    elif re.fullmatch(r'[0-9]+|0[xX][0-9a-fA-F]+', host.removesuffix('.').rsplit('.', 1)[-1]):
        try:
            host = socket.inet_ntoa(socket.inet_aton(host.removesuffix('.')))
        except OSError:
            return 'invalid:'
    default_port = 80 if scheme == 'http' else 443
    return f'{scheme}://{host}' + (f':{port}' if port is not None and port != default_port else '')


def js_api_auto_origin(url: str) -> str | None:
    """
    Return the origin that a page loaded from Python grants the JS API to, or None if it is not
    granted automatically. Plain HTTP from another machine can be modified in transit, so it must
    be listed in ALLOWED_ORIGINS. Loopback HTTP, such as the built-in server, is granted.
    """
    origin = js_api_origin(url)
    if origin.startswith('http://'):
        host = urllib.parse.urlsplit(origin).hostname or ''
        try:
            loopback = host == 'localhost' or ipaddress.ip_address(host).is_loopback
        except ValueError:
            loopback = False
        if not loopback:
            logger.warning(
                'JS API is not enabled automatically on %s, because plain HTTP can be modified '
                "in transit. Use HTTPS or add the origin to webview.settings['ALLOWED_ORIGINS'].",
                url,
            )
            return None
    elif origin.startswith('https://') and webview.settings['IGNORE_SSL_ERRORS']:
        logger.warning(
            'IGNORE_SSL_ERRORS is enabled, so anyone who can intercept the connection to %s can '
            'use its JS API.',
            origin,
        )
    return origin


def _js_api_trusted_origins(window: Window) -> set[str] | None:
    """Origins allowed to use the JS API in the window, or None if every origin is allowed."""
    allowed = webview.settings['ALLOWED_ORIGINS']
    if '*' in allowed:
        return None
    return (window._js_api_origins | {js_api_origin(origin) for origin in allowed}) - {'invalid:'}


def is_js_api_allowed(window: Window, url: str | None) -> bool:
    """Return whether the page at url may use the window's JS API."""
    trusted = _js_api_trusted_origins(window)
    return trusted is None or js_api_origin(url) in trusted


def js_api_guard(window: Window, document: bool = False) -> str:
    """
    Return a Javascript expression that is true only on a page the window's JS API is allowed on.
    It is evaluated in the page itself, which may have navigated since Python last checked it.
    The page cannot spoof location, and the comparison avoids prototype methods it could replace.

    :param document: Check only that the page is still the document whose trust was decided when
        it was injected, rather than checking it against ALLOWED_ORIGINS as it is now.
    """
    if document and window._js_api_document_url is not None:
        trusted: set[str] | None = {js_api_origin(window._js_api_document_url)}
    else:
        trusted = _js_api_trusted_origins(window)
    if trusted is None:
        return 'true'

    origins = sorted(origin for origin in trusted if origin.startswith(('http://', 'https://')))
    documents = sorted(trusted - set(origins))
    return (
        '(function (o, d) { var l = window.location, i; '
        'if (window !== window.top) { return false } '
        'for (i = 0; i < o.length; i++) { if (o[i] === l.origin) { return true } } '
        'for (i = 0; i < d.length; i++) { '
        'if (d[i] === l.href || d[i] + l.hash === l.href) { return true } } '
        f'return false }})({json.dumps(origins)}, {json.dumps(documents)})'
    )


def inject_pywebview(platform: str, window: Window, url: str | None = None) -> None:
    """ "
    Generates and injects a global window.pywebview object. The object contains exposed API functions
    as well as utility functions required by pywebview. The function fires before_load event before
    injecting the object and loaded event after the object is injected.

    :param url: URL of the page that has loaded. Every page gets window.pywebview, so the DOM
        API with its event handlers, evaluate_js and the window UI work everywhere. A page whose
        origin is not allowed to use the JS API gets it without exposed functions, the session
        token or window state, and the bridge accepts only DOM events and evaluate_js results
        from it. None skips the origin check, but the injected script still checks the page's
        actual location before it defines the session token.
    """
    exposed_objects = []

    def get_args(func: object):
        params = list(inspect.getfullargspec(func).args)
        return params

    def get_functions(
        obj: object, base_name: str = '', functions: dict[str, object] | None = None, depth: int = 0
    ):
        if functions is None:
            functions = {}

        # Backstop against runaway recursion into pathological object graphs that generate
        # a fresh object on every attribute access (so the id() guard below never matches).
        # See issue #1838.
        if depth > webview.settings['JS_API_MAX_DEPTH']:
            logger.warning(
                f'Maximum js_api attribute depth ({webview.settings["JS_API_MAX_DEPTH"]}) reached '
                f'while exposing "{base_name}". Nested attributes below this depth are not exposed. '
                'Increase webview.settings["JS_API_MAX_DEPTH"] if this is intended.'
            )
            return functions

        obj_id = id(obj)
        if obj_id in exposed_objects:
            return functions
        else:
            exposed_objects.append(obj_id)

        for name in dir(obj):
            try:
                full_name = f'{base_name}.{name}' if base_name else name
                if name.startswith('_'):
                    continue

                # Never walk into the native GUI object exposed by webview.Window (e.g.
                # when a window is stored on the js_api object). It cannot be bridged to
                # Javascript and its native object tree is effectively unbounded.
                if name == 'native' and isinstance(obj, webview.Window):
                    continue

                attr = getattr(obj, name)
                if not getattr(attr, '_serializable', True):
                    continue

                if inspect.ismethod(attr) or inspect.isfunction(attr):
                    functions[full_name] = get_args(attr)[1:]
                # If the attribute is a class or a non-callable object, make a recursive call
                elif inspect.isclass(attr) or (
                    isinstance(attr, object) and not callable(attr) and hasattr(attr, '__module__')
                ):
                    get_functions(attr, full_name, functions, depth + 1)
            except Exception as e:
                logger.error(f'Error while processing {full_name}: {e}')
                continue

        return functions

    def generate_func():
        if restricted:
            window._js_api_names = frozenset()
            return []

        functions = get_functions(window._js_api)
        # The bridge dispatches only what is advertised here, see js_bridge_call
        window._js_api_names = frozenset(functions)

        if len(window._functions) > 0:
            expose_functions = {name: get_args(f) for name, f in window._functions.items()}
        else:
            expose_functions = {}

        functions.update(expose_functions)

        return [{'func': name, 'params': params} for name, params in functions.items()]

    def generate_js_object():
        try:
            if window._js_api_token != bridge_token:
                return
            window.run_js(js_code)
            logger.debug('_pywebviewready event fired')
            with window._expose_lock:
                if window._js_api_token != bridge_token:
                    return
                func_list = generate_func()
                window.run_js(finish_script % {'functions': json.dumps(func_list)})
                window.events._pywebviewready.set()
                window.events.loaded.set()
                logger.debug('loaded event fired')
        except Exception as e:
            logger.exception(e)
            window.events.loaded.set()

    window.events.before_load.set()

    restricted = url is not None and not is_js_api_allowed(window, url)
    # The trust decision holds for this document until the next navigation, whatever
    # ALLOWED_ORIGINS later becomes, see js_bridge_call and Window._run_js_api_js
    window._js_api_restricted = restricted
    window._js_api_document_url = url
    if restricted:
        # Only worth a warning if the window has something the page now cannot reach
        uses_js_api = window._js_api is not None or bool(window._functions) or bool(window.state)
        (logger.warning if uses_js_api else logger.debug)(
            'window.pywebview.api, window.pywebview.token and window.state are not available '
            "on %s. Add its origin to webview.settings['ALLOWED_ORIGINS'] to allow them.",
            url,
        )
    else:
        window._js_api_pending_html = False

    logger.debug('before_load event fired. injecting pywebview object')
    try:
        # Every document gets a capability; for a restricted page the bridge accepts it only for
        # DOM events and evaluate_js results, see js_bridge_call
        bridge_token = uuid4().hex
        window._js_api_token = bridge_token
        js_code, finish_script = load_js_files(window, platform, restricted)
        if not restricted:
            # Stop the scripts if the page navigated to a disallowed origin before they ran
            guard = f'if (!({js_api_guard(window)})) {{ throw new Error("pywebview: JS API not allowed") }}\n'
            js_code = guard + js_code
            finish_script = guard.replace('%', '%%') + finish_script
    except Exception:
        # Called from native navigation callbacks: Python exceptions must not escape.
        logger.exception('Failed to load pywebview JavaScript')
        window.events.loaded.set()
        return
    thread = Thread(target=generate_js_object)
    thread.start()


def is_js_bridge_token_valid(window: Window, token: str | None) -> bool:
    """Return whether a native bridge message carries the current document's capability."""
    expected = window._js_api_token
    if not expected or not isinstance(token, str) or not hmac.compare_digest(token, expected):
        logger.error('Rejected JS bridge call with an invalid token')
        return False

    return True


# DER bytes of the local HTTP server's certificate, see set_local_tls_cert
_local_tls_cert: bytes | None = None


def pem_to_der(pem: str) -> bytes | None:
    """Return the DER bytes of the first certificate in PEM text, or None if there is none."""
    match = re.search(r'-----BEGIN CERTIFICATE-----(.+?)-----END CERTIFICATE-----', pem, re.S)
    if not match:
        return None
    try:
        return base64.b64decode(''.join(match.group(1).split()), validate=True)
    except ValueError:
        return None


def set_local_tls_cert(certfile: str | None) -> None:
    """
    Remember the certificate of the local HTTP server started with webview.start(ssl=True), or
    forget it when certfile is None. Backends use this rather than their imported webview._state,
    which a reload of webview, as in the test suite, would leave stale.
    """
    global _local_tls_cert
    if certfile is None:
        _local_tls_cert = None
        return
    with open(certfile, encoding='ascii') as f:
        _local_tls_cert = pem_to_der(f.read())


def has_local_tls_cert() -> bool:
    """Return whether the local HTTP server runs with webview.start(ssl=True)."""
    return _local_tls_cert is not None


def is_local_server_url(url: str) -> bool:
    """Return whether url points at an HTTPS server that pywebview started, by its exact origin."""
    from webview import http

    servers = [http.global_server] + [window._server for window in webview.windows]
    origins = {
        js_api_origin(server.address)
        for server in servers
        if server is not None and server.address.startswith('https://')
    }
    return js_api_origin(url) in origins


def is_local_tls_cert(cert: bytes | None) -> bool:
    """Return whether a server certificate, as DER bytes, is the local HTTP server's own."""
    return cert is not None and _local_tls_cert is not None and cert == _local_tls_cert


EXTERNAL_URL_SCHEMES = ('http', 'https', 'mailto')


def open_external_url(url: str, new: int = 0, autoraise: bool = True) -> None:
    """
    Open a link from a page in the system browser. Only web and mailto links are handed to the
    OS, which would otherwise open file: and custom scheme URLs with whatever handler is
    registered for them.
    """
    if urllib.parse.urlsplit(url).scheme.lower() in EXTERNAL_URL_SCHEMES:
        webbrowser.open(url, new, autoraise)
    else:
        logger.warning('Refusing to open %s externally: only http(s) and mailto are allowed', url)


def _page_window_move(window: Window, param: Any) -> tuple[int, int] | None:
    """
    Validate a window move requested by a page, which drag regions send while the user drags.
    Only frameless windows are dragged from the page. Each coordinate is kept within the total
    width or height of all screens, which holds whatever the backend's coordinate origin is.
    """
    if not window.frameless:
        return None
    try:
        x, y = (int(value) for value in param)
    except (TypeError, ValueError, OverflowError):
        return None

    try:
        screens = window.gui.get_screens()
        limit_x = sum(abs(screen.width) for screen in screens)
        limit_y = sum(abs(screen.height) for screen in screens)
    except Exception:
        limit_x = limit_y = 0
    if not limit_x or not limit_y:
        limit_x = limit_y = 100_000

    return max(-limit_x, min(x, limit_x)), max(-limit_y, min(y, limit_y))


def _is_trusted_document(window: Window, source_url: str) -> bool:
    """
    Return whether the current document may use the JS API, as decided when it was injected.
    The sender must also be the document that decision was made for.
    """
    if window._js_api_restricted:
        return False
    if window._js_api_document_url is None:  # injected without a URL to check
        return is_js_api_allowed(window, source_url)
    return js_api_origin(source_url) == js_api_origin(window._js_api_document_url)


# Bridge calls that pages without the JS API may make, see js_bridge_call
DOM_BRIDGE_CALLS = frozenset(('pywebviewEventHandler', 'pywebviewAsyncCallback'))


def js_bridge_call(
    window: Window,
    func_name: str,
    param: Any,
    value_id: str,
    token: str | None = None,
    source_url: str | None = None,
) -> None:
    """
    Calls a function from the JS API and executes it in Python. The function is executed in a separate
    thread to prevent blocking the UI thread. The result is then passed back to the JS API.

    :param source_url: Native URL of the main document. The document-specific token also
        prevents calls from other frames on transports that do not identify the sender frame.
    """

    # Window UI messages, which every page sends, need no token
    if func_name == 'pywebviewMoveWindow':
        move = _page_window_move(window, param)
        if move is not None:
            window.move(*move)
        return

    if not is_js_bridge_token_valid(window, token):
        return

    # Pages from other origins have window.pywebview for the DOM API, but may only report DOM
    # events and evaluate_js results, both of which answer to handlers Python registered
    if source_url is None or (
        func_name not in DOM_BRIDGE_CALLS and not _is_trusted_document(window, source_url)
    ):
        logger.error('Rejected JS bridge call from %s: origin is not allowed', source_url)
        return

    def _call():
        try:
            result = func(*func_params)
            if inspect.isawaitable(result):
                result = run_async(result)
            result = json.dumps(result).replace('\\', '\\\\').replace("'", "\\'")
            retval = f"{{value: '{result}'}}"
        except Exception as e:
            logger.error(traceback.format_exc())
            error = {'message': str(e), 'name': type(e).__name__, 'stack': traceback.format_exc()}
            result = json.dumps(error).replace('\\', '\\\\').replace("'", "\\'")
            retval = f"{{isError: true, value: '{result}'}}"

        # The page may have navigated while the function ran
        window.run_js(
            f'if (({js_api_guard(window, document=True)}) && window.pywebview && '
            f'window.pywebview._bridgeToken === {json.dumps(token)}) {{ '
            f'window.pywebview._returnValuesCallbacks'
            f'[{json.dumps(func_name)}][{json.dumps(value_id)}]({retval}) }}'
        )

    def get_nested_attribute(obj: object, attr_str: str):
        attributes = attr_str.split('.')
        for attr in attributes:
            obj = getattr(obj, attr, None)
            if obj is None:
                return None
        return obj

    if func_name == 'pywebviewEventHandler':
        event = param['event']
        node_id = param['nodeId']
        element = window.dom._elements.get(node_id)

        if not element:
            return

        if event['type'] == 'drop':
            files = event['dataTransfer'].get('files', [])
            for file in files:
                path = [
                    item
                    for item in _dnd_state['paths']
                    if urllib.parse.unquote(item[0]) == file['name']
                ]
                if len(path) == 0:
                    continue

                file['pywebviewFullPath'] = urllib.parse.unquote(path[0][1])
                _dnd_state['paths'].remove(path[0])

        def _call_handler(handler, event):
            try:
                result = handler(event)
                if inspect.isawaitable(result):
                    run_async(result)
            except Exception:
                logger.exception('Error in DOM event handler')

        for handler in element._event_handlers.get(event['type'], []):
            thread = Thread(target=_call_handler, args=(handler, event))
            thread.start()

        return

    if func_name == 'pywebviewAsyncCallback':
        value = json.loads(param) if param is not None else None

        if value_id not in window._callbacks:
            logger.warning(f'No callback registered for value_id {value_id}. Ignoring.')
            return

        callback = window._callbacks[value_id]
        if callable(callback):
            result = callback(value)
            # The bridge may be called on the GUI thread, so do not block it on a coroutine
            if inspect.isawaitable(result):
                Thread(target=run_async, args=(result,)).start()
        else:
            logger.error(
                f'Async function executed and callback is not callable. Returned value {value}'
            )

        del window._callbacks[value_id]
        return

    if func_name == 'pywebviewStateUpdate':
        try:
            # Store as a state value: __setattr__ would let a page reach State's private attributes
            window.state._set_state_value(param['key'], param['value'], False)
        except Exception:
            logger.exception('Error occurred while updating state key %s', param.get('key'))
        return

    if func_name == 'pywebviewStateDelete':
        special_key = '__pywebviewHaltUpdate__' + param
        try:
            delattr(window.state, special_key)
        except AttributeError:
            # The key was already removed on the Python side (e.g. a race with a
            # concurrent delete or update); nothing left to do on the JS side.
            pass
        except Exception:
            logger.exception('Error occurred while deleting state key %s', param)
        return

    func = window._functions.get(func_name)
    if func is None and func_name in window._js_api_names:
        func = get_nested_attribute(window._js_api, func_name)

    if func is not None:
        try:
            func_params = param
            thread = Thread(target=_call)
            thread.start()
        except Exception:
            logger.exception('Error occurred while evaluating function %s', func_name)
    else:
        logger.error('Function %s() does not exist', func_name)


def load_js_files(window: Window, platform: str, restricted: bool = False) -> tuple[str, str]:
    """
    Load JS files in the order they should be loaded.
    The order is api, the rest and finish.js.
    Return the concatenated JS code and the finish script, which must be loaded last and
    separately in order to

    :param restricted: Load them for a page that may not use the JS API: without the session
        token and the window state.
    """
    js_dir = get_js_dir()
    logger.debug('Loading JS files from %s', js_dir)
    js_files = glob(os.path.join(glob_escape(js_dir), '**', '*.js'), recursive=True)
    ordered_js_files = sort_js_files(js_files)
    js_code = ''
    finish_script = ''

    for file in ordered_js_files:
        with open(file) as f:
            name = os.path.splitext(os.path.basename(file))[0]
            content = f.read()
            params = {}

            if name == 'api':
                params = {
                    'token': '' if restricted else _TOKEN,
                    'bridge_token': window._js_api_token or '',
                    'platform': platform,
                    'uid': window.uid,
                    'js_api_endpoint': window.js_api_endpoint,
                }
            elif name == 'customize':
                params = _customize_params(window, platform)
            elif name == 'state':
                state = {} if restricted else window.state
                params = {'state': escape_string(json.dumps(state))}
            elif name == 'finish':
                finish_script = content
                continue

            try:
                js_code += content % params
            except (KeyError, TypeError, ValueError) as e:
                raise WebViewException(f'Failed to format JavaScript file {file!r}: {e}') from e

    return js_code, finish_script


def _customize_params(window: Window, platform: str) -> dict[str, Any]:
    return {
        'text_select': str(window.text_select),
        'drag_selector': webview.settings['DRAG_REGION_SELECTOR'],
        'drag_region_direct_target_only': str(webview.settings['DRAG_REGION_DIRECT_TARGET_ONLY']),
        'zoomable': str(window.zoomable),
        'draggable': str(window.draggable),
        'easy_drag': str(
            platform in ('edgechromium', 'winui3') and window.easy_drag and window.frameless
        ),
    }


def get_js_dir() -> str:
    """
    Get the path to the directory with Javascript files.
    """
    path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'js')

    if os.path.exists(path):
        return path

    # try py2app frozen path. This is hacky, but it works.
    # See https://github.com/r0x0r/pywebview/issues/1565
    if '.zip' in path:
        base_path = path.split('.zip')[0]
        dir = os.path.dirname(base_path)

        for file in os.listdir(dir):
            if file.startswith('python') and os.path.isdir(os.path.join(dir, file)):
                js_path = os.path.join(dir, file, 'webview', 'js')
                if os.path.exists(js_path):
                    return js_path

    raise FileNotFoundError(f'Cannot find JS directory in {path}')


def sort_js_files(js_files: list[str]) -> list[str]:
    """
    Sorts JS files in the order they should be loaded. API first, then state, then the rest and
    finally finish.js that fires a pywebviewready event.
    """
    LOAD_ORDER = {'api': 0, 'state': 1}

    ordered_js_files = []
    remaining_js_files = []

    for file in js_files:
        basename = os.path.splitext(os.path.basename(file))[0]
        if basename not in LOAD_ORDER:
            ordered_js_files.append(file)
        else:
            remaining_js_files.append((basename, file))

    for basename, file in sorted(remaining_js_files, key=lambda x: LOAD_ORDER[x[0]]):
        ordered_js_files.insert(LOAD_ORDER[basename], file)

    return ordered_js_files


def escape_string(string: str) -> str:
    return (
        string.replace('\\', '\\\\')
        .replace('"', r'\"')
        .replace('\n', r'\n')
        .replace('\r', r'\r')
        .replace("'", r'\'')
        .replace('\u2028', r'\u2028')
        .replace('\u2029', r'\u2029')
    )


def inject_base_uri(content: str, base_uri: str) -> str:
    pattern = r'<%s(?:[\s]+[^>]*|)>'
    base_tag = f'<base href="{base_uri}">'

    match = re.search(pattern % 'base', content)

    if match:
        return content

    match = re.search(pattern % 'head', content)
    if match:
        tag = match.group()
        return content.replace(tag, tag + base_tag)

    match = re.search(pattern % 'html', content)
    if match:
        tag = match.group()
        return content.replace(tag, tag + base_tag)

    match = re.search(pattern % 'body', content)
    if match:
        tag = match.group()
        return content.replace(tag, base_tag + tag)

    return base_tag + content


def interop_dll_path(dll_name: str) -> str:
    def candidate_paths(base_dir: str) -> list[str]:
        if os.environ.get('PYTHONNET_RUNTIME') == 'netfx' and dll_name in (
            'Microsoft.Web.WebView2.Core.dll',
            'Microsoft.Web.WebView2.WinForms.dll',
        ):
            # The flat WinForms assembly targets .NET Core; netfx needs the framework pair.
            return [os.path.join(base_dir, 'net462', dll_name)]
        return [
            os.path.join(base_dir, dll_name),
            os.path.join(base_dir, 'runtimes', dll_name, 'native'),
        ]

    # Unfrozen path
    lib_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
    for candidate in candidate_paths(lib_dir):
        if os.path.exists(candidate):
            return candidate

    # Frozen path, dll in the same dir as the executable
    for candidate in candidate_paths(os.path.dirname(os.path.realpath(sys.argv[0]))):
        if os.path.exists(candidate):
            return candidate

    try:
        # Frozen path packed as onefile
        if hasattr(sys, '_MEIPASS'):  # Pyinstaller
            for candidate in candidate_paths(sys._MEIPASS):
                if os.path.exists(candidate):
                    return candidate
        elif getattr(sys, 'frozen', False):  # cx_freeze
            for candidate in candidate_paths(os.path.dirname(sys.executable)):
                if os.path.exists(candidate):
                    return candidate
    except Exception:
        pass

    raise FileNotFoundError(f'Cannot find {dll_name}')


def environ_append(key: str, *values: str, sep: str = ' ') -> None:
    """Append values to an environment variable, separated by sep"""
    value_list = list(values)

    existing = os.environ.get(key, '')
    if existing:
        value_list = [existing] + value_list

    os.environ[key] = sep.join(value_list)


def css_to_camel(css_case_string: str) -> str:
    words = css_case_string.split('-')
    camel_case_string = words[0] + ''.join(word.capitalize() for word in words[1:])
    return camel_case_string


def android_jar_path() -> str:
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib', 'pywebview-android.jar')


def stringify_headers(headers: dict[str, Any]) -> dict[str, str]:
    return {k: str(v) for k, v in headers.items()}
