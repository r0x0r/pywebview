from __future__ import annotations

import inspect
import logging
import os
from collections.abc import Callable, Mapping, Sequence
from enum import Flag, auto
from functools import wraps
from threading import Lock
from typing import Any, Concatenate, TypeAlias, TypeVar
from urllib.parse import urljoin
from uuid import uuid1

from typing_extensions import ParamSpec

import webview.http as http
from webview.dom.dom import DOM
from webview.errors import JavascriptException, WebViewException
from webview.event import Event, EventContainer, in_blocking_handler
from webview.localization import original_localization
from webview.menu import Menu
from webview.screen import Screen
from webview.state import State
from webview.util import (
    abspath,
    escape_string,
    is_app,
    is_local_url,
    js_api_auto_origin,
    js_api_guard,
    js_api_origin,
    parse_file_type,
)
from webview.util import base_uri as get_base_uri

P = ParamSpec('P')
T = TypeVar('T')

logger = logging.getLogger('pywebview')


def _api_call(function: WindowFunc[P, T], event_type: str) -> WindowFunc[P, T]:
    """
    Decorator to call a pywebview API, checking for _webview_ready and raisings
    appropriate Exceptions on failure.
    """

    @wraps(function)
    def wrapper(self: Window, *args: P.args, **kwargs: P.kwargs) -> T:
        event = getattr(self.events, event_type)

        if not event.is_set() and in_blocking_handler():
            # A blocking handler holds up the very events being waited for (before_show runs
            # before shown, before_load before loaded), so it calls through to the backend
            # directly. The JS bridge cannot exist yet though, so fail at once instead.
            if event_type == '_pywebviewready':
                raise WebViewException(
                    f'{function.__name__}() cannot be called before the page has loaded'
                )
        elif not event.wait(20):
            raise WebViewException('Main window failed to start')

        if self.gui is None:
            raise WebViewException('GUI is not initialized')

        return function(self, *args, **kwargs)

    return wrapper


def _shown_call(function: WindowFunc[P, T]) -> WindowFunc[P, T]:
    return _api_call(function, 'shown')


def _loaded_call(function: WindowFunc[P, T]) -> WindowFunc[P, T]:
    return _api_call(function, 'loaded')


def _before_load_call(function: WindowFunc[P, T]) -> WindowFunc[P, T]:
    return _api_call(function, 'before_load')


def _pywebview_ready_call(function: WindowFunc[P, T]) -> WindowFunc[P, T]:
    return _api_call(function, '_pywebviewready')


class FixPoint(Flag):
    NORTH = auto()
    WEST = auto()
    EAST = auto()
    SOUTH = auto()


class Window:
    def __init__(
        self,
        uid: str,
        title: str,
        url: str | Callable[..., Any] | None,
        html: str = '',
        width: int = 800,
        height: int = 600,
        x: int | None = None,
        y: int | None = None,
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
        js_api: Any = None,
        text_select: bool = False,
        transparent: bool = False,
        zoomable: bool = False,
        draggable: bool = False,
        vibrancy: bool = False,
        menu: list[Menu] | None = None,
        localization: Mapping[str, str] | None = None,
        http_port: int | None = None,
        server: type[http.BottleServer] | None = None,
        server_args: http.ServerArgs | None = None,
        screen: Screen | None = None,
    ) -> None:
        self.uid = uid
        self._title = title
        self.original_url = None if html else url  # original URL provided by user
        self.real_url: str | None = None
        self.html = html
        self.initial_width = width
        self.initial_height = height
        self.initial_x = x
        self.initial_y = y
        self.resizable = resizable
        self.fullscreen = fullscreen
        self.min_size = min_size
        self.confirm_close = confirm_close
        self.background_color = background_color
        self.text_select = text_select
        self.frameless = frameless
        self.easy_drag = easy_drag
        self.shadow = shadow
        self.focus = focus
        self.hidden = hidden
        self.on_top = on_top
        self.minimized = minimized
        self.maximized = maximized
        self.transparent = transparent
        self.zoomable = zoomable
        self.draggable = draggable
        self.localization_override = localization
        self.vibrancy = vibrancy
        self.screen = screen
        self.menu = menu if menu is not None else []

        # Server config
        self._http_port = http_port
        self._server_class = server
        self._server_args = server_args if server_args is not None else {}

        # HTTP server path magic
        self._url_prefix: str | None = None
        self._common_path: str | None = None
        self._server: http.BottleServer | None = None

        self._js_api = js_api
        self._functions: dict[str, Callable[..., Any]] = {}
        # js_api attribute paths advertised to Javascript on the current page
        self._js_api_names: frozenset[str] = frozenset()
        # Origins of the pages loaded from Python, which may use the JS API
        self._js_api_origins: set[str] = set()
        self._js_api_token: str | None = None
        # Trust decided for the current document when it was injected, see inject_pywebview.
        # Nothing is trusted until then, and a navigation resets it.
        self._js_api_restricted = True
        self._js_api_document_url: str | None = None
        self._js_api_pending_html = False
        self._callbacks: dict[str, Callable[..., Any] | None] = {}

        self.events = EventContainer()
        self.events.closed = Event(self)
        self.events.closing = Event(self, True)
        self.events.loaded = Event(self)
        self.events.before_load = Event(self, True)
        self.events.before_show = Event(self, True)
        self.events.initialized = Event(self, True)
        self.events.shown = Event(self)
        self.events.minimized = Event(self)
        self.events.maximized = Event(self)
        self.events.restored = Event(self)
        self.events.resized = Event(self)
        self.events.moved = Event(self)
        self.events.request_sent = Event(self, True)
        self.events.response_received = Event(self)

        self.events._pywebviewready = Event(self)
        self.events.closed += self._stop_server

        self._expose_lock = Lock()
        self.dom = DOM(self)
        self.gui: Any = None
        self.native: Any = None  # set in the gui after window creation
        self._state = State(self)

    def _initialize(self, gui: Any, server: http.BottleServer | None = None):
        self.gui = gui

        self.localization = original_localization.copy()
        if self.localization_override:
            self.localization.update(self.localization_override)

        if is_app(self.original_url) and (server is None or server == http.global_server):
            server = self._create_server(self.original_url)
        elif server is None:
            server = http.global_server

        self._url_prefix = server.address if server is not None else None
        self._common_path = server.common_path if server is not None else None
        self._server = server
        self.real_url = self._resolve_url(self.original_url)
        self._allow_js_api_on(self.real_url)

        abort = self.events.initialized.set(gui.renderer)
        return not abort

    @property
    @_shown_call
    def width(self) -> int:
        width, _ = self.gui.get_size(self.uid)
        return width

    @property
    @_shown_call
    def height(self) -> int:
        _, height = self.gui.get_size(self.uid)
        return height

    @property
    def state(self) -> State:
        return self._state

    @state.setter
    def state(self, state: State) -> None:
        if not isinstance(state, State):
            raise TypeError('State must be an instance of State class')
        self._state = state

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    @_loaded_call
    def title(self, title: str) -> None:
        self._title = title
        self.gui.set_title(title, self.uid)

    @property
    @_shown_call
    def x(self) -> int:
        x, _ = self.gui.get_position(self.uid)
        return x

    @property
    @_shown_call
    def y(self) -> int:
        _, y = self.gui.get_position(self.uid)
        return y

    @property
    def on_top(self) -> bool:
        return self.__on_top

    @on_top.setter
    def on_top(self, on_top: bool) -> None:
        self.__on_top = on_top
        if hasattr(self, 'gui') and self.gui is not None:
            self.gui.set_on_top(self.uid, on_top)

    @_shown_call
    def load_url(self, url: str) -> None:
        """
        Load a new URL into a previously created WebView window. This function must be invoked after WebView windows is
        created with create_window(). Otherwise an exception is thrown.
        :param url: url to load
        :param uid: uid of the target instance
        """
        if is_app(url) or (is_local_url(url) and not self._server_serves(url)):
            self._stop_server()
            self._server = self._create_server(url)
            self._url_prefix = self._server.address
            self._common_path = self._server.common_path

        self.real_url = self._resolve_url(url)
        self._js_api_pending_html = False
        self._allow_js_api_on(self.real_url)
        self.events.loaded.clear()
        self.events.before_load.clear()
        self.events._pywebviewready.clear()

        logger.debug(f'Loading URL: {self.real_url}')
        self.gui.load_url(self.real_url, self.uid)

    @_shown_call
    def load_html(self, html: str, base_uri: str | None = None) -> None:
        """
        Load a new HTML content into a previously created WebView window. This function must be invoked after WebView windows is
        created with create_window(). Otherwise an exception is thrown.
        :param html: HTML content to load.
        :param base_uri: Base URI for resolving links. Default is the directory of the application entry point.
        """
        if base_uri is None:
            base_uri = get_base_uri()

        self._invalidate_js_api()
        self._allow_js_api_on(None)
        self._allow_js_api_on(base_uri)
        self.events.loaded.clear()
        self.events.before_load.clear()
        self.events._pywebviewready.clear()
        logger.debug(f'Loading HTML: {html[:30]}')
        self.gui.load_html(html, base_uri, self.uid)

    @_loaded_call
    def load_css(self, stylesheet: str) -> None:
        """ "
        Load a CSS stylesheet into the current web view window
        """
        sanitized_css = stylesheet.replace('\n', '').replace('\r', '').replace('"', "'")
        js_code = f'pywebview._loadCss("{sanitized_css}")'
        self.run_js(js_code)

    @_shown_call
    def set_title(self, title: str) -> None:
        """
        Set a new title of the window
        """
        self._title = title
        self.gui.set_title(title, self.uid)

    @_loaded_call
    def clear_cookies(self):
        """
        Clear all the cookies
        """
        return self.gui.clear_cookies(self.uid)

    @_loaded_call
    def get_cookies(self):
        """
        Get cookies for the current website
        """
        # only reachable unloaded from a blocking handler, which skips the readiness wait
        if not self.events.loaded.is_set():
            raise WebViewException('get_cookies() cannot be called before the page has loaded')

        return self.gui.get_cookies(self.uid)

    @_loaded_call
    def get_current_url(self) -> str | None:
        """
        Get the URL currently loaded in the target webview
        """
        return self.gui.get_current_url(self.uid)

    @_shown_call
    def destroy(self) -> None:
        """
        Destroy a web view window
        """
        self.gui.destroy_window(self.uid)

    @_shown_call
    def show(self) -> None:
        """
        Show a web view window.
        """
        self.gui.show(self.uid)

    @_shown_call
    def hide(self) -> None:
        """
        Hide a web view window.
        """
        self.gui.hide(self.uid)

    @_shown_call
    def set_window_size(self, width: int, height: int) -> None:
        """
        Resize window
        :param width: desired width of target window
        :param height: desired height of target window
        """
        logger.warning(
            'This function is deprecated and will be removed in future releases. Use resize() instead'
        )
        self.resize(width, height)

    @_shown_call
    def resize(
        self, width: int, height: int, fix_point: FixPoint = FixPoint.NORTH | FixPoint.WEST
    ) -> None:
        """
        Resize window
        :param width: desired width of target window
        :param height: desired height of target window
        :param fix_point: Fix window to specified point during resize.
            Must be of type FixPoint. Different points can be combined
            with bitwise operators.
            Example: FixPoint.NORTH | FixPoint.WEST
        """
        self.gui.resize(width, height, self.uid, fix_point)

    @_shown_call
    def maximize(self) -> None:
        """
        Maximize window.
        """
        self.gui.maximize(self.uid)

    @_shown_call
    def minimize(self) -> None:
        """
        Minimize window.
        """
        self.gui.minimize(self.uid)

    @_shown_call
    def restore(self) -> None:
        """
        Restore minimized window.
        """
        self.gui.restore(self.uid)

    @_shown_call
    def toggle_fullscreen(self) -> None:
        """
        Toggle fullscreen mode
        """
        self.gui.toggle_fullscreen(self.uid)

    @_shown_call
    def move(self, x: int, y: int) -> None:
        """
        Move Window
        :param x: desired x coordinate of target window
        :param y: desired y coordinate of target window
        """
        self.gui.move(x, y, self.uid)

    @_before_load_call
    def run_js(self, script: str) -> Any:
        """
        Run JavaScript code as is without any modifications. Result of the code is
        not guaranteed to be returned and depends on the platform
        :param script: JavaScript code to run
        """
        return self.gui.evaluate_js(script, self.uid, False)

    @_pywebview_ready_call
    def evaluate_js(self, script: str, callback: Callable[..., Any] | None = None) -> Any:
        """
        Evaluate given JavaScript code and return the result. The code is executed in eval statement
        in order to support returning the last evaluated value in the script without the return statement.
        Promises are supported and resolved values are returned to the callback function.
        Exceptions are caught and rethrown as JavascriptException in Python code. Javascript code is
        evaluated synchronously and the result is returned to the caller.
        :param script: The JavaScript code to be evaluated
        :callback: Optional callback function that will be called for resolved promises
        :return: Return value of the evaluated code

        """
        unique_id = uuid1().hex
        if callback:
            self._callbacks[unique_id] = callback

        if self.gui.renderer == 'cef':
            return_result = (
                f'window.external.return_result(pywebview.stringify(value), "{unique_id}");'
            )
        elif self.gui.renderer == 'android-webkit':
            return_result = 'return pywebview.stringify(value);'
        else:
            return_result = 'pywebview.stringify(value);'

        if callback:
            handle_promise = f"""
                if (pywebview._isPromise(value)) {{
                    value.then(function evaluate_async(result) {{
                        pywebview._asyncCallback(pywebview.stringify(result), "{unique_id}")
                    }}).catch(function evaluate_async(error) {{
                        pywebview._asyncCallback(pywebview.stringify(error), "{unique_id}")
                    }});
                    value = {{ pywebviewPromise420: true }};
                }}
            """
        else:
            handle_promise = ''

        escaped_script = f"""
            var value;
            try {{
                value = eval("{escape_string(script)}");
                {handle_promise}
            }} catch (e) {{
                value = {{
                    name: e.name,
                    pywebviewJavascriptError420: true,
                }}
                var keys = Object.getOwnPropertyNames(e);
                keys.forEach(function(key) {{ value[key] = e[key] }})
            }}
            {return_result};
        """

        if self.gui.renderer == 'cef':
            result = self.gui.evaluate_js(escaped_script, self.uid, True, unique_id)
        elif self.gui.renderer == 'android-webkit':
            escaped_script = f"""
                (function() {{
                    {escaped_script}
                }})()
            """
            result = self.gui.evaluate_js(escaped_script, self.uid, True)
        else:
            result = self.gui.evaluate_js(escaped_script, self.uid, True)

        if callback:
            if isinstance(result, dict) and result.get('pywebviewPromise420'):
                return None

            # no promise to resolve, so the callback will never be called. None is ambiguous, as
            # Qt's fallback without a result handler returns None, so keep the callback then
            if result is not None:
                self._callbacks.pop(unique_id, None)

        if isinstance(result, dict) and result.get('pywebviewJavascriptError420'):
            del result['pywebviewJavascriptError420']
            raise JavascriptException(result)
        else:
            return result

    @_shown_call
    def create_confirmation_dialog(self, title: str, message: str) -> bool:
        """
        Create a confirmation dialog
        :param title: Dialog title
        :param message: Dialog detail message
        :return: True for OK, False for Cancel
        """

        return self.gui.create_confirmation_dialog(title, message, self.uid)

    @_shown_call
    def create_file_dialog(
        self,
        dialog_type: int = 10,
        directory: str = '',
        allow_multiple: bool = False,
        save_filename: str = '',
        file_types: Sequence[str] = tuple(),
    ) -> Sequence[str] | None:
        """
        Create a file dialog
        :param dialog_type: Dialog type: open file (FileDialog.OPEN), save file (FileDialog.SAVE), open folder (FileDialog.FOLDER). Default
                            is open file.
        :param directory: Initial directory
        :param allow_multiple: Allow multiple selection. Default is false.
        :param save_filename: Default filename for save file dialog.
        :param file_types: Allowed file types in open file dialog. Should be a tuple of strings in the format:
            filetypes = ('Description (*.extension[;*.extension[;...]])', ...)
        :return: A tuple of selected files, None if cancelled.
        """
        for f in file_types:
            parse_file_type(f)

        if not os.path.exists(directory):
            directory = ''

        return self.gui.create_file_dialog(
            dialog_type, directory, allow_multiple, save_filename, file_types, self.uid
        )

    def expose(self, *functions: Callable[..., Any]) -> None:
        if not all(map(callable, functions)):
            raise TypeError('Parameter must be a function')

        func_list: list[dict[str, Any]] = []

        with self._expose_lock:
            for func in functions:
                name = func.__name__
                self._functions[name] = func
                params = list(inspect.getfullargspec(func).args)
                func_list.append({'func': name, 'params': params})

        if self.events.loaded.is_set() and not self._run_js_api_js(
            f'window.pywebview._createApi({func_list})'
        ):
            logger.warning(
                'Exposed functions are not available on %s. Add its origin to '
                "webview.settings['ALLOWED_ORIGINS'] to allow them.",
                self._js_api_document_url or 'the current page',
            )

    def _allow_js_api_on(self, url: str | None) -> None:
        """Allow the JS API on the origin of a page loaded from Python. None means HTML content."""
        origin = js_api_auto_origin(url) if url else 'about:blank'
        if origin is None:
            return
        self._js_api_origins.add(origin)
        if origin == 'about:blank':
            self._js_api_pending_html = True

    def _invalidate_js_api(self) -> None:
        """Revoke bridge access at the native backend's document transition."""
        self._js_api_token = None
        self._js_api_restricted = True
        self._js_api_document_url = None
        if not self._js_api_pending_html:
            self._js_api_origins.discard('about:blank')

    def _run_js_api_js(self, script: str) -> bool:
        """
        Run pywebview's own script only if the current document may use the JS API. Return
        whether it was sent. The script also checks the page's location, in case the page has
        navigated since it was injected.
        """
        if self._js_api_restricted:
            return False
        self.run_js(f'if ({js_api_guard(self, document=True)}) {{ {script} }}')
        return True

    def _create_server(self, url: str | Callable[..., Any]) -> http.BottleServer:
        """Start a server dedicated to this window, configured like the one in start()."""
        from webview import _state

        *_, server = http.start_server(
            [url],
            http_port=self._http_port,
            server=self._server_class or _state['server'],
            **(self._server_args or _state['server_args']),
        )
        return server

    def _stop_server(self) -> None:
        """Stop the server dedicated to this window, if it has one."""
        import webview

        server = self._server
        if server is not None and server is not http.global_server:
            self._server = None
            # Revoke the JS API on the server's origin before releasing its port, which
            # another process could then bind
            origin = js_api_origin(server.address)
            for window in {self, *webview.windows}:
                window._js_api_origins.discard(origin)
            if hasattr(server, 'stop'):
                server.stop()

    def _server_serves(self, url: str) -> bool:
        """Return True if the window's current server can serve the local URL."""
        server = self._server
        if server is None or not server.running:
            return False
        if not getattr(server, 'serves_files', True):
            # A route of the WSGI app, unless the URL is an absolute path to an existing file
            path = url.split('#')[0].split('?')[0]
            return not (os.path.isabs(path) and os.path.isfile(path))
        if not server.root_path:
            return False

        path = os.path.normcase(abspath(url.split('#')[0].split('?')[0]))
        root = os.path.normcase(server.root_path)
        try:
            return os.path.commonpath([path, root]) == root
        except ValueError:  # paths on different drives
            return False

    def _resolve_url(self, url: str | Callable[..., Any] | None) -> str | None:
        if is_app(url):
            return self._url_prefix
        if not isinstance(url, str):
            return None
        if is_local_url(url) and self._url_prefix and self._common_path is not None:
            filename = os.path.relpath(url, self._common_path)
            return urljoin(self._url_prefix, filename)
        return url


WindowFunc: TypeAlias = Callable[Concatenate[Window, P], T]
