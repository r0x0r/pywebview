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
from http.cookies import SimpleCookie
from platform import architecture
from threading import Thread
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import webview

from .js import api, dom, mouse, event, npo

if TYPE_CHECKING:
    from .window import Window

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


class WebViewException(Exception):
    pass


def is_app(url: str | None) -> bool:
    """Returns true if 'url' is a WSGI or ASGI app."""
    return callable(url)


def is_local_url(url: str | None) -> bool:
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

    if getattr(sys, 'frozen', False):  # cx_freeze
        return os.path.dirname(sys.executable)

    if 'pytest' in sys.modules:
        for arg in reversed(sys.argv):
            path = os.path.realpath(arg.split('::')[0])
            if os.path.exists(path):
                return path if os.path.isdir(path) else os.path.dirname(path)

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
        cookie = SimpleCookie[str]()
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


def parse_api_js(window: Window, platform: str, uid: str = '') -> str:
    def get_args(func: object):
        params = list(inspect.getfullargspec(func).args)
        return params

    def generate_func():
        if window._js_api:
            functions = {
                name: get_args(getattr(window._js_api, name))[1:]
                for name in dir(window._js_api)
                if inspect.ismethod(getattr(window._js_api, name)) and not name.startswith('_')
            }
        else:
            functions = {}

        if len(window._functions) > 0:
            expose_functions = {name: get_args(f) for name, f in window._functions.items()}
        else:
            expose_functions = {}

        functions.update(expose_functions)
        functions = functions.items()

        return [{'func': name, 'params': params} for name, params in functions]

    try:
        func_list = generate_func()
    except Exception as e:
        logger.exception(e)
        func_list = []

    js_code = (
        npo.src
        + event.src
        + api.src
        % {
            'token': _TOKEN,
            'platform': platform,
            'uid': uid,
            'func_list': func_list,
            'js_api_endpoint': window.js_api_endpoint,
        }
        + dom.src
        + mouse.src
        % {
            'drag_selector': webview.DRAG_REGION_SELECTOR,
            'zoomable': str(window.zoomable).lower(),
            'draggable': str(window.draggable).lower(),
            'easy_drag': str(platform == 'chromium' and window.easy_drag and window.frameless).lower(),
        }
    )
    
    return js_code


def js_bridge_call(window: Window, func_name: str, param: Any, value_id: str) -> None:
    def _call():
        try:
            result = func(*func_params.values())
            result = json.dumps(result).replace('\\', '\\\\').replace("'", "\\'")
            code = f'window.pywebview._returnValues["{func_name}"]["{value_id}"] = {{value: \'{result}\'}}'
        except Exception as e:
            print(traceback.format_exc())
            error = {'message': str(e), 'name': type(e).__name__, 'stack': traceback.format_exc()}
            result = json.dumps(error).replace('\\', '\\\\').replace("'", "\\'")
            code = f'window.pywebview._returnValues["{func_name}"]["{value_id}"] = {{isError: true, value: \'{result}\'}}'

        window.evaluate_js(code)

    if func_name == 'moveWindow':
        window.move(*param)
        return

    if func_name == 'asyncCallback':
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

    func = window._functions.get(func_name) or getattr(window._js_api, func_name, None)

    if func is not None:
        try:
            func_params = param
            thread = Thread(target=_call)
            thread.start()
        except Exception:
            logger.exception('Error occurred while evaluating function %s', func_name)
    else:
        logger.error('Function %s() does not exist', func_name)


def escape_string(string: str) -> str:
    return (
        string.replace('\\', '\\\\').replace('"', r"\"").replace('\n', r'\n').replace('\r', r'\r')
    )


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
