import os
from functools import wraps

from webview.event import Event
from webview.util import base_uri, parse_file_type, escape_string, transform_url, make_unicode, WebViewException
from .js import css


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
    def __init__(self, uid, title, url, html, width, height, resizable, fullscreen,
                 min_size, confirm_close, background_color, js_api, text_select, frameless):
        self.uid = uid
        self.title = make_unicode(title)
        self.url = None if html else transform_url(url)
        self.html = html
        self.width = width
        self.height = height
        self.resizable = resizable
        self.fullscreen = fullscreen
        self.min_size = min_size
        self.confirm_close = confirm_close
        self.background_color = background_color
        self.js_api = js_api
        self.text_select = text_select
        self.frameless = frameless

        self.loaded = Event()
        self.shown = Event()
        self.gui = None

    def _set_gui(self, gui):
        self.gui = gui

    @_shown_call
    def load_url(self, url):
        """
        Load a new URL into a previously created WebView window. This function must be invoked after WebView windows is
        created with create_window(). Otherwise an exception is thrown.
        :param url: url to load
        :param uid: uid of the target instance
        """
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
        content = make_unicode(content)
        self.gui.load_html(content, base_uri, self.uid)

    @_loaded_call
    def load_css(self, stylesheet):
        code = css.src % stylesheet.replace('\n', '').replace('\r', '').replace('"', "'")
        self.gui.evaluate_js(code, self.uid)

    @_shown_call
    def set_title(self, title):
        """
        Sets a new title of the window
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
    def toggle_fullscreen(self):
        """
        Toggle fullscreen mode
        """
        self.gui.toggle_fullscreen(self.uid)

    @_shown_call
    def set_window_size(self, width, height):
        """
        Set Window Size
        :param width: desired width of target window
        :param height: desired height of target window
        """
        self.gui.set_window_size(width, height, self.uid)

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
