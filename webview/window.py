import inspect
import logging
import os
from enum import Flag, auto
from functools import wraps
from uuid import uuid1

from webview.event import Event
from webview.localization import original_localization
from webview.serving import resolve_url
from webview.util import base_uri, parse_file_type, escape_string, make_unicode, WebViewException
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
            raise WebViewException('Create a web view window first, before invoking this function')

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
    def __init__(self, uid, title, url, html, width, height, x, y, resizable, fullscreen,
                 min_size, hidden, frameless, easy_drag, minimized, on_top, confirm_close,
                 background_color, js_api, text_select, transparent, localization):
        self.uid = uid
        self.title = make_unicode(title)
        self.original_url = None if html else url  # original URL provided by user
        self.real_url = None  # transformed URL for internal HTTP server
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
        self.localization_override = localization

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

        self._closed = self.events.closed
        self._closing = self.events.closing
        self._loaded = self.events.loaded
        self._shown = self.events.shown

        self.gui = None
        self._is_http_server = False

    def _initialize(self, gui, multiprocessing, http_server):
        self.gui = gui
        self.events.loaded._initialize(multiprocessing)
        self.events.shown._initialize(multiprocessing)
        self._is_http_server = http_server

        # WebViewControl as of 5.1.1 crashes on file:// urls. Stupid workaround to make it work
        if (
            gui.renderer == "edgehtml" and
            self.original_url and
            isinstance(self.original_url, str) and
            (self.original_url.startswith('file://') or '://' not in self.original_url)
        ):
            self._is_http_server = True

        self.real_url = resolve_url(self.original_url, self._is_http_server)

        self.localization = original_localization.copy()
        if self.localization_override:
            self.localization.update(self.localization_override)

    @property
    def shown(self):
        logger.warning('shown event is deprecated and will be removed in 4.0. Use events.shown instead')
        return self.events.shown

    @shown.setter
    def shown(self, value):
        self.events.shown = value

    @property
    def loaded(self):
        logger.warning('loaded event is deprecated and will be removed in 4.0. Use events.loaded instead')
        return self.events.loaded

    @loaded.setter
    def shown(self, value):
        self.events.loaded = value

    @property
    def closed(self):
        logger.warning('closed event is deprecated and will be removed in 4.0. Use events.closed instead')
        return self.events.closed

    @closed.setter
    def closed(self, value):
        self.events.closed = value

    @property
    def closing(self):
        logger.warning('closing event is deprecated and will be removed in 4.0. Use events.closing instead')
        return self.events.closed

    @closing.setter
    def closing(self, value):
        self.on_closing = value

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
            raise NotImplementedError('get_elements requires WebKit2 2.2 or greater')

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
        self.url = url
        self.real_url = resolve_url(url, self._is_http_server or self.gui.renderer == 'edgehtml')

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

        content = make_unicode(content)
        self.gui.load_html(content, base_uri, self.uid)

    @_loaded_call
    def load_css(self, stylesheet):
        code = css.src % stylesheet.replace('\n', '').replace('\r', '').replace('"', "'")
        self.gui.evaluate_js(code, self.uid)

    @_shown_call
    def set_title(self, title):
        """
        Set a new title of the window
        """
        self.gui.set_title(title, self.uid)

    @_loaded_call
    def get_current_url(self):
        """
        Get the URL currently loaded in the target webview
        """
        return self.gui.get_current_url(self.uid)

    @_shown_call
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
        logger.warning('This function is deprecated and will be removed in future releases. Use resize() instead')
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
            sync_eval = 'window.external.return_result(JSON.stringify(value), "{0}");'.format(unique_id,)
        else:
            sync_eval = 'JSON.stringify(value);'


        if callback:
            escaped_script = """
                var value = eval("{0}");
                if (pywebview._isPromise(value)) {{
                    value.then(function evaluate_async(result) {{
                        pywebview._asyncCallback(JSON.stringify(result), "{1}")
                    }});
                    true;
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
                params = list(inspect.getfullargspec(func).args) # Python 3
            except AttributeError:
                params = list(inspect.getargspec(func).args)  # Python 2


            func_list.append({
                'func': name,
                'params': params
            })

        if self.events.loaded.is_set():
            self.evaluate_js('window.pywebview._createApi(%s)' % func_list)
