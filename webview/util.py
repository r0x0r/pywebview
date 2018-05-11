# -*- coding: utf-8 -*-

"""
(C) 2014-2018 Roman Sirokov and contributors
Licensed under BSD license

http://github.com/r0x0r/pywebview/
"""

import os
import re
import sys
import platform

from .js import api, npo


def base_uri(relative_path=''):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        if 'pytest' in sys.modules:
            path = os.path.realpath(sys.argv[1])
            base_path = path if os.path.isdir(path) else os.path.dirname(path)
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


def parse_api_js(api_instance):
    func_list = [str(f) for f in dir(api_instance) if callable(getattr(api_instance, f)) and str(f)[0] != '_']
    js_code = npo.src + api.src % func_list

    return js_code


def escape_string(string):
    return string\
        .replace('\\', '\\\\') \
        .replace('"', r'\"') \
        .replace('\n', r'\n')\
        .replace('\r', r'\r')


def transform_url(url):
    if url and ':' not in url:
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
    pattern = '<%s(?:[\s]+[^>]*|)>'
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


def interop_dll_path():
    dll_name = 'WebBrowserInterop.x64.dll' if platform.architecture()[0] == '64bit' else 'WebBrowserInterop.x86.dll'

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

    raise Exception('Cannot find WebBrowserInterop.dll')