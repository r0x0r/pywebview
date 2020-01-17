import inspect
import logging
import os
from functools import wraps

from webview.event import Event
from webview.http_server import start_server
from webview.util import base_uri, parse_file_type, escape_string, transform_url, make_unicode, WebViewException
from .js import css


logger = logging.getLogger('pywebview')


def _api_call(function, event_type):
    """
    Decorator to call a pywebview API, checking for _webview_ready and raisings
    appropriate Exceptions on failure.
    """
    @wraps(function)
    def wrapper(*args, **kwargs):
        event = args[0].loaded if event_type == 'loaded' else args[0].shown

        try:
            if not event.wait(15):
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


class Window:
    def __init__(self, uid, title, url, html, width, height, x, y, resizable, fullscreen,
                 min_size, hidden, frameless, minimized, confirm_close, background_color,
                 js_api, text_select):
        self.uid = uid
        self.title = make_unicode(title)
        self.url = None if html else transform_url(url)
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
        self.hidden = hidden
        self.minimized = minimized

        self._js_api = js_api
        self._functions = {}

        self.closed = Event()
        self.closing = Event()
        self.loaded = Event()
        self.shown = Event()

        self.gui = None
        self._httpd = None
        self._is_http_server = False

    def _initialize(self, gui, multiprocessing, http_server):
        self.gui = gui
        self.loaded._initialize(multiprocessing)
        self.shown._initialize(multiprocessing)
        self._is_http_server = http_server

        if http_server and self.url and self.url.startswith('file://'):
            self.url, self._httpd = start_server(self.url)

    @property
    def width(self):
        self.shown.wait(15)
        width, _ = self.gui.get_size(self.uid)
        return width

    @property
    def height(self):
        self.shown.wait(15)
        _, height = self.gui.get_size(self.uid)
        return height

    @property
    def x(self):
        self.shown.wait(15)
        x, _ = self.gui.get_position(self.uid)
        return x

    @property
    def y(self):
        self.shown.wait(15)
        _, y = self.gui.get_position(self.uid)
        return y

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
        if self._httpd:
            self._httpd.shutdown()
            self._httpd = None

        url = transform_url(url)

        if (self._is_http_server or self.gui.renderer == 'edgehtml') and url.startswith('file://'):
            url, self._httpd = start_server(url)

        self.gui.load_url(url, self.uid)

    @_shown_call
    def load_html(self, content, base_uri=base_uri()):
        """
        Load a new content into a previously created WebView window. This function must be invoked after WebView windows is
        created with create_window(). Otherwise an exception is thrown.
        :param content: Content to load.
        :param base_uri: Base URI for resolving links. Default is the directory of the application entry point.
        :param uid: uid of the target instance
        """

        if self._httpd:
            self._httpd.shutdown()

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
        self.gui.resize(width, height, self.uid)

    @_shown_call
    def resize(self, width, height):
        """
        Resize window
        :param width: desired width of target window
        :param height: desired height of target window
        """
        self.gui.resize(width, height, self.uid)

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
    def evaluate_js(self, script):
        """
        Evaluate given JavaScript code and return the result
        :param script: The JavaScript code to be evaluated
        :return: Return value of the evaluated code
        """
        escaped_script = 'JSON.stringify(eval("{0}"))'.format(escape_string(script))
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

            params = list(inspect.getfullargspec(func).args)

            func_list.append({
                'func': name,
                'params': params
            })

        if self.loaded.is_set():
            self.evaluate_js('window.pywebview._createApi(%s)' % func_list)
