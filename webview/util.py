"""
(C) 2014-2019 Roman Sirokov and contributors
Licensed under BSD license

http://github.com/r0x0r/pywebview/
"""
from __future__ import annotations

import inspect
import json
import logging
import os
import re
import sys
import traceback
from collections import UserDict
from glob import glob
from http.cookies import SimpleCookie
from platform import architecture
from threading import Thread
from typing import TYPE_CHECKING, Any, Callable
from uuid import uuid4

import webview

from webview.dom import _dnd_state
from webview.errors import WebViewException
import urllib.parse

if TYPE_CHECKING:
    from webview.window import Window

_TOKEN = uuid4().hex

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


class ImmutableDict(UserDict):
    """"
    A dictionary that does not allow adding new keys or deleting existing ones.
    Only existing keys can be modified.
    """

    def __init__(self, initial_data=None, **kwargs):
        self.data = {}
        if initial_data:
            self.data.update(initial_data)
        if kwargs:
            self.data.update(kwargs)

    def __setitem__(self, key, value):
        if key not in self.data:
            raise KeyError(f"Cannot add new key '{key}'. Only existing keys can be modified.")
        super().__setitem__(key, value)

    def __delitem__(self, key):
        raise KeyError('Deleting keys is not allowed.')


def is_app(url: str | callable | None) -> bool:
    """Returns true if 'url' is a WSGI or ASGI app."""
    return callable(url)


def is_local_url(url: str | callable | None) -> bool:
    return not ((is_app(url)) or (
            (not url) or (url.startswith('http://')) or (url.startswith('https://')) or url.startswith('file://')))


def needs_server(urls: list[str]) -> bool:
    return bool([url for url in urls if (is_app(url) or is_local_url(url))])


def get_app_root() -> str:
    """
    Gets the file root of the application.
    """

    if hasattr(sys, '_MEIPASS'):  # Pyinstaller
        return sys._MEIPASS

    if os.getenv('RESOURCEPATH'): # py2app
        return os.getenv('RESOURCEPATH')

    if getattr(sys, 'frozen', False):  # cx_freeze
        return os.path.dirname(sys.executable)

    if 'pytest' in sys.modules and os.getenv('PYWEBVIEW_TEST'):
        return os.path.join(os.path.dirname(__file__), '..', 'tests')

    if hasattr(sys, 'getandroidapilevel'):
        return os.getenv('ANDROID_APP_PATH')

    return os.path.dirname(os.path.realpath(sys.argv[0]))


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


def create_cookie(input_: dict[Any, Any] | str) -> SimpleCookie[str]:
    if isinstance(input_, dict):
        cookie = SimpleCookie()
        name = input_['name']
        cookie[name] = input_['value']
        cookie[name]['path'] = input_['path']
        cookie[name]['domain'] = input_['domain']
        cookie[name]['expires'] = input_['expires']
        cookie[name]['secure'] = input_['secure']
        cookie[name]['httponly'] = input_['httponly']

        if sys.version_info.major >= 3 and sys.version_info.minor >= 8:
            cookie[name]['samesite'] = input_.get('samesite')

        return cookie

    if isinstance(input_, str):
        return SimpleCookie(input_)

    raise WebViewException('Unknown input to create_cookie')


def parse_file_type(file_type: str) -> tuple[str, str]:
    """
    :param file_type: file type string 'description (*.file_extension1;*.file_extension2)' as required by file filter in create_file_dialog
    :return: (description, file extensions) tuple
    """
    valid_file_filter = r'^([\w ]+)\((\*(?:\.(?:\w+|\*))*(?:;\*\.\w+)*)\)$'
    match = re.search(valid_file_filter, file_type)

    if match:
        return match.group(1).rstrip(), match.group(2)
    raise ValueError(f'{file_type} is not a valid file filter')


def inject_pywebview(platform: str, window: Window) -> str:
    """"
    Generates and injects a global window.pywebview object. The object contains exposed API functions
    as well as utility functions required by pywebview. The function fires before_load event before
    injecting the object and loaded event after the object is injected.
    """
    exposed_objects = []

    def get_args(func: object):
        params = list(inspect.getfullargspec(func).args)
        return params

    def get_functions(obj: object, base_name: str = '', functions: dict[str, object] = None):
        obj_id = id(obj)
        if obj_id in exposed_objects:
            return functions
        else:
            exposed_objects.append(obj_id)

        if functions is None:
            functions = {}

        for name in dir(obj):
            try:
                full_name = f"{base_name}.{name}" if base_name else name
                target_obj = getattr(obj, name)

                if name.startswith('_') or getattr(target_obj, '_serializable', True) == False:
                    continue

                attr = getattr(obj, name)
                if inspect.ismethod(attr):
                    functions[full_name] = get_args(attr)[1:]
                # If the attribute is a class or a non-callable object, make a recursive call
                elif inspect.isclass(attr) or (isinstance(attr, object) and not callable(attr) and hasattr(attr, "__module__")):
                    get_functions(attr, full_name, functions)
            except Exception as e:
                logger.error(f'Error while processing {full_name}: {e}')
                continue

        return functions

    def generate_func():
        functions = get_functions(window._js_api)

        if len(window._functions) > 0:
            expose_functions = {name: get_args(f) for name, f in window._functions.items()}
        else:
            expose_functions = {}

        functions.update(expose_functions)

        return [{'func': name, 'params': params} for name, params in functions.items()]

    def generate_js_object():
        window.run_js(js_code)
        window.events._pywebviewready.set()
        logger.debug('_pywebviewready event fired')

        try:
            with window._expose_lock:
                func_list = generate_func()
                window.run_js(finish_script % {
                    'functions': json.dumps(func_list)
                })
                window.events.loaded.set()
                logger.debug('loaded event fired')
        except Exception as e:
            logger.exception(e)
            window.events.loaded.set()

    window.events.before_load.set()
    logger.debug('before_load event fired. injecting pywebview object')
    js_code, finish_script = load_js_files(window, platform)
    thread = Thread(target=generate_js_object)
    thread.start()


def inject_state(window: Window):
    """ Inject state after page is loaded"""

    json_string = json.dumps(window.state)

def js_bridge_call(window: Window, func_name: str, param: Any, value_id: str) -> None:
    """
    Calls a function from the JS API and executes it in Python. The function is executed in a separate
    thread to prevent blocking the UI thread. The result is then passed back to the JS API.
    """
    def _call():
        try:
            result = func(*func_params)
            result = json.dumps(result).replace('\\', '\\\\').replace("'", "\\'")
            retval = f"{{value: \'{result}\'}}"
        except Exception as e:
            logger.error(traceback.format_exc())
            error = {'message': str(e), 'name': type(e).__name__, 'stack': traceback.format_exc()}
            result = json.dumps(error).replace('\\', '\\\\').replace("'", "\\'")
            retval = f"{{isError: true, value: \'{result}\'}}"

        window.evaluate_js(f'window.pywebview._returnValuesCallbacks["{func_name}"]["{value_id}"]({retval})')

    def get_nested_attribute(obj: object, attr_str: str):
        attributes = attr_str.split('.')
        for attr in attributes:
            obj = getattr(obj, attr, None)
            if obj is None:
                return None
        return obj

    if func_name == 'pywebviewMoveWindow':
        window.move(*param)
        return

    if func_name == 'pywebviewEventHandler':
        event = param['event']
        node_id = param['nodeId']
        element = window.dom._elements.get(node_id)

        if not element:
            return

        if event['type'] == 'drop':
            files = event['dataTransfer'].get('files', [])
            for file in files:
                path = [item for item in _dnd_state['paths'] if urllib.parse.unquote(item[0]) == file['name']]
                if len(path) == 0:
                    continue

                file['pywebviewFullPath'] = urllib.parse.unquote(path[0][1])
                _dnd_state['paths'].remove(path[0])

        for handler in element._event_handlers.get(event['type'], []):
            thread = Thread(target=handler, args=(event,))
            thread.start()

        return

    if func_name == 'pywebviewAsyncCallback':
        value = json.loads(param) if param is not None else None

        if callable(window._callbacks[value_id]):
            window._callbacks[value_id](value)
        else:
            logger.error(
                'Async function executed and callback is not callable. Returned value {0}'.format(
                    value
                )
            )

        del window._callbacks[value_id]
        return

    if func_name == 'pywebviewStateUpdate':
        window.state.__setattr__(param['key'], param['value'], False)
        return

    if func_name == 'pywebviewStateDelete':
        special_key = '__pywebviewHaltUpdate__' + param
        delattr(window.state, special_key)
        return

    func = window._functions.get(func_name) or get_nested_attribute(window._js_api, func_name)

    if func is not None:
        try:
            func_params = param
            thread = Thread(target=_call)
            thread.start()
        except Exception:
            logger.exception(
                'Error occurred while evaluating function %s', func_name)
    else:
        logger.error('Function %s() does not exist', func_name)


def load_js_files(window: Window, platform: str) -> str:
    """
    Load JS files in the order they should be loaded.
    The order is polyfill, api, the rest and finish.js.
    Return the concatenated JS code and the finish script, which must be loaded last and
    separately in order to
    """
    js_dir = get_js_dir()
    logger.debug('Loading JS files from %s', js_dir)
    js_files = glob(os.path.join(js_dir, '**', '*.js'), recursive=True)
    ordered_js_files = sort_js_files(js_files)
    js_code = ''
    finish_script = ''

    for file in ordered_js_files:
        with open(file, 'r') as f:
            name = os.path.splitext(os.path.basename(file))[0]
            content = f.read()
            params = {}

            if name == 'api':
                params = {
                    'token': _TOKEN,
                    'platform': platform,
                    'uid': window.uid,
                    'js_api_endpoint': window.js_api_endpoint
                }
            elif name == 'customize':
                params = {
                    'text_select': str(window.text_select),
                    'drag_selector': webview.settings['DRAG_REGION_SELECTOR'],
                    'zoomable': str(window.zoomable),
                    'draggable': str(window.draggable),
                    'easy_drag': str(platform == 'edgechromium' and window.easy_drag and window.frameless)
                }
            elif name == 'state':
                params = {
                    'state': json.dumps(window.state)
                }
            elif name == 'finish':
                finish_script = content
                continue
            elif name == 'polyfill' and platform != 'mshtml':
                continue

            js_code += content % params

    return js_code, finish_script


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

    raise FileNotFoundError('Cannot find JS directory in %s' % path)


def sort_js_files(js_files: list[str]) -> list[str]:
    """
    Sorts JS files in the order they should be loaded. Polyfill first, then API, then the rest and
    finally finish.js that fires a pywebviewready event.
    """
    LOAD_ORDER = { 'polyfill': 0, 'api': 1, 'state': 2 }

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
        string.replace('\\', '\\\\').replace('"', r"\"").replace('\n', r'\n').replace('\r', r'\r')
    )


def escape_quotes(string: str) -> str:
    if isinstance(string, str):
        return string.replace('"', r"\"").replace("'", r"\'")
    else:
        return string


def escape_line_breaks(string: str) -> str:
    return string.replace('\\n', '\\\\n').replace('\\r', '\\\\r')


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
    if dll_name == 'WebBrowserInterop.dll':
        dll_name = (
            'WebBrowserInterop.x64.dll'
            if architecture()[0] == '64bit'
            else 'WebBrowserInterop.x86.dll'
        )

    # Unfrozen path
    dll_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib', dll_name)
    if os.path.exists(dll_path):
        return dll_path

    dll_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), 'lib', 'runtimes', dll_name, 'native'
    )
    if os.path.exists(dll_path):
        return dll_path

    # Frozen path, dll in the same dir as the executable
    dll_path = os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), dll_name)
    if os.path.exists(dll_path):
        return dll_path

    try:
        # Frozen path packed as onefile
        if hasattr(sys, '_MEIPASS'):  # Pyinstaller
            dll_path = os.path.join(sys._MEIPASS, dll_name)

        elif getattr(sys, 'frozen', False):  # cx_freeze
            dll_path = os.path.join(sys.executable, dll_name)

        if os.path.exists(dll_path):
            return dll_path
    except Exception:
        pass

    raise FileNotFoundError(f'Cannot find {dll_name}')


def environ_append(key: str, *values: str, sep=' ') -> None:
    '''Append values to an environment variable, separated by sep'''
    values = list(values)

    existing = os.environ.get(key, '')
    if existing:
        values = [existing] + values

    os.environ[key] = sep.join(values)


def css_to_camel(css_case_string: str) -> str:
    words = css_case_string.split('-')
    camel_case_string = words[0] + ''.join(word.capitalize() for word in words[1:])
    return camel_case_string


def android_jar_path() -> str:
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib', 'pywebview-android.jar')


def stringify_headers(headers: dict[str, Any]) -> dict[str, str]:
    return {k: str(v) for k, v in headers.items()}