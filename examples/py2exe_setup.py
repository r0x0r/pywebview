"""
This is an example of py2exe setup.py script for freezing your pywebview application

Usage:
    python setup.py py2exe
"""

from distutils.core import setup

import sys
import py2exe
import os

# ModuleFinder can't handle runtime changes to __path__, but win32com uses them
try:
    # py2exe 0.6.4 introduced a replacement modulefinder.
    # This means we have to add package paths there, not to the built-in
    # one.  If this new modulefinder gets integrated into Python, then
    # we might be able to revert this some day.
    # if this doesn't work, try import modulefinder
    try:
        import py2exe.mf as modulefinder
    except ImportError:
        import modulefinder
    import win32com, sys
    for p in win32com.__path__[1:]:
        modulefinder.AddPackagePath("win32com", p)
    for extra in ["win32com.shell"]: #,"win32com.mapi"
        __import__(extra)
        m = sys.modules[extra]
        for p in m.__path__[1:]:
            modulefinder.AddPackagePath(extra, p)
except ImportError:
    # no build path setup, no worries.
    pass


def tree(src):
    return [(root, map(lambda f: os.path.join(root, f), files)) for (root, dirs, files) in os.walk(os.path.normpath(src))]


ENTRY_POINT = ['YOUR_EXAMPLE.py']
DATA_FILES = tree('DATA_FILES_DIR') + tree('DATA_FILE_DIR2_ETC')

OPTIONS = {
    # bundling application (bundle_files = 1) does not work for some reason.
    # if you figure it out, drop me a line
    'bundle_files': 3,
    'compressed': False,
    'includes': ['win32gui', 'win32con', 'win32api', 'win32ui', 'ctypes', 'comtypes', 'webview']}

setup(
    data_files=DATA_FILES,
    options={'py2exe': OPTIONS},
    setup_requires=['py2exe'],
    windows=[{
        'script': ENTRY_POINT,
        'icon_resources': [(1, 'icon.ico')]
    }],
    zipfile=None)
