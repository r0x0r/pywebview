import inspect
import logging
import os
from enum import Flag, auto
from functools import wraps
from urllib.parse import urljoin
from uuid import uuid1

import webview.http as http

from webview.event import Event
from webview.localization import original_localization
from webview.util import base_uri, parse_file_type, is_app, is_local_url, needs_server, escape_string, WebViewException
from .js import css


logger = logging.getLogger('pywebview')


def _api_call(function, event_type):
    """
    Decorator to call a pywebview API, checking for _webview_ready and raisings
    appropriate Exceptions on failure.
    """
    @wraps(function)
    def wrapper(*args, **kwargs):
        event = args[0].events.loaded if event_type == 'loaded' else args[0].events.shown

        try:
            if not event.wait(20):
                raise WebViewException('Main window failed to start')

            if args[0].gui is None:
                raise WebViewException('GUI is not initialized')

            return function(*args, **kwargs)
        except NameError as e:
            raise WebViewException(
                'Create a web view window first, before invoking this function')

    return wrapper


def _shown_call(function):
    return _api_call(function, 'shown')


def _loaded_call(function):
    return _api_call(function, 'loaded')


class FixPoint(Flag):
    NORTH = auto()
    WEST = auto()
    EAST = auto()
    SOUTH = auto()


class EventContainer:
    pass


class Window:
    def __init__(self, uid, title, url, html='', width=800, height=600, x=None, y=None,
                 resizable=True, fullscreen=False, min_size=(200, 100), hidden=False,
                 frameless=False, easy_drag=True, minimized=False, on_top=False, confirm_close=False, background_color='#FFFFFF',
                 js_api=None, text_select=False, transparent=False, zoomable=False, draggable=False, vibrancy=False, localization=None,
                 http_port=None, server=None, server_args={}):
        self.uid = uid
        self.title = title
        self.original_url = None if html else url  # original URL provided by user
        self.real_url = None
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
        self.hidden = hidden
        self.on_top = on_top
        self.minimized = minimized
        self.transparent = transparent
        self.zoomable = zoomable
        self.draggable = draggable
        self.localization_override = localization
        self.vibrancy = vibrancy

        # Server config
        self._http_port = http_port
        self._server = server
        self._server_args = server_args

        # HTTP server path magic
        self._url_prefix = None
        self._common_path = None
        self._server = None

        self._js_api = js_api
        self._functions = {}
        self._callbacks = {}

        self.events = EventContainer()
        self.events.closed = Event()
        self.events.closing = Event(True)
        self.events.loaded = Event()
        self.events.shown = Event()
        self.events.minimized = Event()
        self.events.maximized = Event()
        self.events.restored = Event()
        self.events.resized = Event()
        self.events.moved = Event()

        self.gui = None

    def _initialize(self, gui, server=None):
        self.gui = gui

        self.localization = original_localization.copy()
        if self.localization_override:
            self.localization.update(self.localization_override)

        if is_app(self.original_url) and (server is None or server == http.global_server):
            prefix, common_path, server = http.start_server(
                urls=[self.original_url], http_port=self._http_port, server=self._server, **self._server_args)
        elif server is None:
            server = http.global_server

        self._url_prefix = server.address if not server is None else None
        self._common_path = server.common_path if not server is None else None
        self._server = server
        self.js_api_endpoint = http.global_server.js_api_endpoint if not http.global_server is None else None
        self.real_url = self._resolve_url(self.original_url)

    @property
    def width(self):
        self.events.shown.wait(15)
        width, _ = self.gui.get_size(self.uid)
        return width

    @property
    def height(self):
        self.events.shown.wait(15)
        _, height = self.gui.get_size(self.uid)
        return height

    @property
    def x(self):
        self.events.shown.wait(15)
        x, _ = self.gui.get_position(self.uid)
        return x

    @property
    def y(self):
        self.events.shown.wait(15)
        _, y = self.gui.get_position(self.uid)
        return y

    @property
    def on_top(self):
        return self.__on_top

    @on_top.setter
    def on_top(self, on_top):
        self.__on_top = on_top
        if hasattr(self, 'gui') and self.gui != None:
            self.gui.set_on_top(self.uid, on_top)

    @_loaded_call
    def get_elements(self, selector):
        # check for GTK's WebKit2 version
        if hasattr(self.gui, 'old_webkit') and self.gui.old_webkit:
            raise NotImplementedError(
                'get_elements requires WebKit2 2.2 or greater')

        code = """
            var elements = document.querySelectorAll('%s');
            var serializedElements = [];

            for (var i = 0; i < elements.length; i++) {
                var node = pywebview.domJSON.toJSON(elements[i], {
                    metadata: false,
                    serialProperties: true
                });
                serializedElements.push(node);
            }

            serializedElements;
        """ % selector

        return self.evaluate_js(code)

    @_shown_call
    def load_url(self, url):
        """
        Load a new URL into a previously created WebView window. This function must be invoked after WebView windows is
        created with create_window(). Otherwise an exception is thrown.
        :param url: url to load
        :param uid: uid of the target instance
        """
        if ((self._server is None) or (not self._server.running)) and ((is_app(url) or is_local_url(url))):
            self._url_prefix, self._common_path, self.server = http.start_server([
                                                                                 url])

        self.real_url = self._resolve_url(url)
        self.gui.load_url(self.real_url, self.uid)

    @_shown_call
    def load_html(self, content, base_uri=base_uri()):
        """
        Load a new content into a previously created WebView window. This function must be invoked after WebView windows is
        created with create_window(). Otherwise an exception is thrown.
        :param content: Content to load.
        :param base_uri: Base URI for resolving links. Default is the directory of the application entry point.
        :param uid: uid of the target instance
        """
        self.gui.load_html(content, base_uri, self.uid)

    @_loaded_call
    def load_css(self, stylesheet):
        code = css.src % stylesheet.replace(
            '\n', '').replace('\r', '').replace('"', "'")
        self.gui.evaluate_js(code, self.uid)

    @_shown_call
    def set_title(self, title):
        """
        Set a new title of the window
        """
        self.gui.set_title(title, self.uid)

    @_loaded_call
    def get_cookies(self):
        """
        Get cookies for the current website
        """
        return self.gui.get_cookies(self.uid)

    @_loaded_call
    def get_current_url(self):
        """
        Get the URL currently loaded in the target webview
        """
        return self.gui.get_current_url(self.uid)

    @_loaded_call
    def destroy(self):
        """
        Destroy a web view window
        """
        self.gui.destroy_window(self.uid)

    @_shown_call
    def show(self):
        """
        Show a web view window.
        """
        self.gui.show(self.uid)

    @_shown_call
    def hide(self):
        """
        Hide a web view window.
        """
        self.gui.hide(self.uid)

    @_shown_call
    def set_window_size(self, width, height):
        """
        Resize window
        :param width: desired width of target window
        :param height: desired height of target window
        """
        logger.warning(
            'This function is deprecated and will be removed in future releases. Use resize() instead')
        self.resize(width, height)

    @_shown_call
    def resize(self, width, height, fix_point=FixPoint.NORTH | FixPoint.WEST):
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
    def minimize(self):
        """
        Minimize window.
        """
        self.gui.minimize(self.uid)

    @_shown_call
    def restore(self):
        """
        Restore minimized window.
        """
        self.gui.restore(self.uid)

    @_shown_call
    def toggle_fullscreen(self):
        """
        Toggle fullscreen mode
        """
        self.gui.toggle_fullscreen(self.uid)

    @_shown_call
    def move(self, x, y):
        """
        Move Window
        :param x: desired x coordinate of target window
        :param y: desired y coordinate of target window
        """
        self.gui.move(x, y, self.uid)

    @_loaded_call
    def evaluate_js(self, script, callback=None):
        """
        Evaluate given JavaScript code and return the result
        :param script: The JavaScript code to be evaluated
        :return: Return value of the evaluated code
        :callback: Optional callback function that will be called for resolved promises
        """
        unique_id = uuid1().hex
        self._callbacks[unique_id] = callback

        if self.gui.renderer == 'cef':
            sync_eval = 'window.external.return_result(JSON.stringify(value), "{0}");'.format(
                unique_id,)
        else:
            sync_eval = 'JSON.stringify(value);'

        if callback:
            escaped_script = """
                var value = eval("{0}");
                if (pywebview._isPromise(value)) {{
                    value.then(function evaluate_async(result) {{
                        pywebview._asyncCallback(JSON.stringify(result), "{1}")
                    }});
                    "true";
                }} else {{ {2} }}
            """.format(escape_string(script), unique_id, sync_eval)
        else:
            escaped_script = """
                var value = eval("{0}");
                {1};
            """.format(escape_string(script), sync_eval)

        if self.gui.renderer == 'cef':
            return self.gui.evaluate_js(escaped_script, self.uid, unique_id)
        else:
            return self.gui.evaluate_js(escaped_script, self.uid)

    @_shown_call
    def create_confirmation_dialog(self, title, message):
        """
        Create a confirmation dialog
        :param title: Dialog title
        :param message: Dialog detail message
        :return: True for OK, False for Cancel
        """

        return self.gui.create_confirmation_dialog(title, message, self.uid)

    @_shown_call
    def create_file_dialog(self, dialog_type=10, directory='', allow_multiple=False, save_filename='', file_types=()):
        """
        Create a file dialog
        :param dialog_type: Dialog type: open file (OPEN_DIALOG), save file (SAVE_DIALOG), open folder (OPEN_FOLDER). Default
                            is open file.
        :param directory: Initial directory
        :param allow_multiple: Allow multiple selection. Default is false.
        :param save_filename: Default filename for save file dialog.
        :param file_types: Allowed file types in open file dialog. Should be a tuple of strings in the format:
            filetypes = ('Description (*.extension[;*.extension[;...]])', ...)
        :return: A tuple of selected files, None if cancelled.
        """
        if type(file_types) != tuple and type(file_types) != list:
            raise TypeError('file_types must be a tuple of strings')
        for f in file_types:
            parse_file_type(f)

        if not os.path.exists(directory):
            directory = ''

        return self.gui.create_file_dialog(dialog_type, directory, allow_multiple, save_filename, file_types, self.uid)

    def expose(self, *functions):
        if not all(map(callable, functions)):
            raise TypeError('Parameter must be a function')

        func_list = []

        for func in functions:
            name = func.__name__
            self._functions[name] = func

            try:
                params = list(inspect.getfullargspec(func).args)  # Python 3
            except AttributeError:
                params = list(inspect.getargspec(func).args)  # Python 2

            func_list.append({
                'func': name,
                'params': params
            })

        if self.events.loaded.is_set():
            self.evaluate_js('window.pywebview._createApi(%s)' % func_list)

    def expose_class(self, cls):
        if not inspect.isclass(cls):
            raise TypeError('Parameter must be a class')

        def get_methods(cls, prefix=cls.__name__):
            func_list = []
            for name, func in cls.__dict__.items():
                if inspect.isclass(func):
                    full_name = prefix + "." + name
                    func_list.extend(get_methods(func, prefix=full_name))
                elif callable(func) and not name.startswith('__'):
                    full_name = prefix + "." + name
                    self._functions[full_name] = func
                    try:
                        params = list(inspect.getfullargspec(
                            func).args)  # Python 3
                    except AttributeError:
                        params = list(inspect.getargspec(
                            func).args)  # Python 2
                    func_list.append({
                        'func': full_name,
                        'params': params
                    })
            return func_list

        func_list = get_methods(cls)
        if self.events.loaded.is_set():
            self.evaluate_js('window.pywebview._createApi(%s)' % func_list)

    def _resolve_url(self, url):
        if is_app(url):
            return self._url_prefix
        if is_local_url(url) and self._url_prefix and self._common_path is not None:
            filename = os.path.relpath(url, self._common_path)
            return urljoin(self._url_prefix, filename)
        else:
            return url
