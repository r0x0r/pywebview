from distutils.core import setup

import sys
import os
import shutil


def tree(src):
    return [(root, map(lambda f: os.path.join(root, f), filter(lambda f: os.path.splitext(f)[1] != ".map", files))) for (root, dirs, files) in os.walk(os.path.normpath(src))]


APP = ['start.py']
DATA_FILES = tree('assets')
OPTIONS_OSX = {'argv_emulation': False,
               'strip': True,
               'includes': ['WebKit', 'Foundation', 'webview']}

if os.path.exists('build'):
    shutil.rmtree('build')

if os.path.exists('dist'):
    shutil.rmtree('dist')

if sys.platform == 'darwin':
    import py2app

    setup(
        app=APP,
        data_files=DATA_FILES,
        options={'py2app': OPTIONS_OSX},
        setup_requires=['py2app'],
    )
