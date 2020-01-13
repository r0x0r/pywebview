# -*- coding: utf-8 -*-

"""
(C) 2014-2019 Roman Sirokov and contributors
Licensed under BSD license

http://github.com/r0x0r/pywebview/
"""

import inspect
import json
import logging
import os
import re
import sys
import traceback
from platform import architecture
from threading import Thread
from uuid import uuid4

from .js import api, npo, dom, event

_token = uuid4().hex

default_html = '<!doctype html><html><head></head><body></body></html>'

logger = logging.getLogger('pywebview')


class WebViewException(Exception):
    pass


def base_uri(relative_path=''):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        if 'pytest' in sys.modules:
            for arg in reversed(sys.argv):
                path = os.path.realpath(arg.split('::')[0])
                if os.path.exists(path):
                    base_path = path if os.path.isdir(path) else os.path.dirname(path)
                    break
        else:
            base_path = os.path.dirname(os.path.realpath(sys.argv[0]))

    if not os.path.exists(base_path):
        raise ValueError('Path %s does not exist' % base_path)

    return 'file://%s' % os.path.join(base_path, relative_path)


def convert_string(string):
    if sys.version < '3':
        return unicode(string)
    else:
        return str(string)


def parse_file_type(file_type):
    '''
    :param file_type: file type string 'description (*.file_extension1;*.file_extension2)' as required by file filter in create_file_dialog
    :return: (description, file extensions) tuple
    '''
    valid_file_filter = r'^([\w ]+)\((\*(?:\.(?:\w+|\*))*(?:;\*\.\w+)*)\)$'
    match = re.search(valid_file_filter, file_type)

    if match:
        return match.group(1).rstrip(), match.group(2)
    else:
        raise ValueError('{0} is not a valid file filter'.format(file_type))


def parse_api_js(window, platform, uid=''):
    def get_args(f):
        return list(inspect.getfullargspec(f).args)

    def generate_func():
        if window._js_api:
            functions = { name: get_args(getattr(window._js_api, name))[1:] for name in dir(window._js_api) if callable(getattr(window._js_api, name)) and not name.startswith('_')}
        else:
            functions = {}

        if len(window._functions) > 0:
            expose_functions = { name: get_args(f) for name, f in window._functions.items()}
        else:
            expose_functions = {}

        functions.update(expose_functions)
        functions = functions.items()

        return [ {'func': name, 'params': params} for name, params in functions ]

    try:
        func_list = generate_func()
    except Exception as e:
        logger.exception(e)

    js_code = npo.src + event.src + api.src % (_token, platform, uid, func_list) + dom.src
    return js_code


def js_bridge_call(window, func_name, param, value_id):
    def _call():
        try:
            result = func(*func_params.values())
            result = json.dumps(result).replace('\\', '\\\\').replace('\'', '\\\'')
            code = 'window.pywebview._returnValues["{0}"]["{1}"] = {{value: \'{2}\'}}'.format(func_name, value_id, result)
        except Exception as e:
            error = {
                'message': str(e),
                'name': type(e).__name__,
                'stack': traceback.format_exc()
            }
            result = json.dumps(error).replace('\\', '\\\\').replace('\'', '\\\'')
            code = 'window.pywebview._returnValues["{0}"]["{1}"] = {{isError: true, value: \'{2}\'}}'.format(func_name, value_id, result)

        window.evaluate_js(code)

    func = window._functions.get(func_name) or getattr(window._js_api, func_name, None)

    if func is not None:
        try:
            func_params = param if not param else json.loads(param)
            t = Thread(target=_call)
            t.start()
        except Exception:
            logger.exception('Error occurred while evaluating function {0}'.format(func_name))
    else:
        logger.error('Function {}() does not exist'.format(func_name))


def escape_string(string):
    return string\
        .replace('\\', '\\\\') \
        .replace('"', r'\"') \
        .replace('\n', r'\n')\
        .replace('\r', r'\r')


def transform_url(url):
    if url and '://' not in url:
        return base_uri(url)
    else:
        return url


def make_unicode(string):
    """
    Python 2 and 3 compatibility function that converts a string to Unicode. In case of Unicode, the string is returned
    unchanged
    :param string: input string
    :return: Unicode string
    """
    if sys.version < '3' and isinstance(string, str):
        return unicode(string.decode('utf-8'))

    return string


def escape_line_breaks(string):
    return string.replace('\\n', '\\\\n').replace('\\r', '\\\\r')


def inject_base_uri(content, base_uri):
    pattern = r'<%s(?:[\s]+[^>]*|)>'
    base_tag = '<base href="%s">' % base_uri

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


def interop_dll_path(dll_name):
    if dll_name == 'WebBrowserInterop.dll':
        dll_name = 'WebBrowserInterop.x64.dll' if architecture()[0] == '64bit' else 'WebBrowserInterop.x86.dll'

    # Unfrozen path
    dll_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib', dll_name)
    if os.path.exists(dll_path):
        return dll_path

    # Frozen path, dll in the same dir as the executable
    dll_path = os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), dll_name)
    if os.path.exists(dll_path):
        return dll_path

    try:
        # Frozen path packed as onefile
        dll_path = os.path.join(sys._MEIPASS, dll_name)
        if os.path.exists(dll_path):
            return dll_path
    except Exception:
        pass

    raise Exception('Cannot find %s' % dll_name)

