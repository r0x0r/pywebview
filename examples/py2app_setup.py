"""
This is an example of py2applet setup.py script for freezing your pywebview application

Usage:
    python setup.py py2app
"""
import sys
import os
from setuptools import setup

APP = ['YOUR_EXAMPLE.py']
DATA_FILES = []
OPTIONS_OSX = {'argv_emulation': False,
           'strip': True,
           'iconfile': 'icon.icns',
           'includes': ['WebKit', 'Foundation', 'webview']}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS_OSX},
    setup_requires=['py2app'],
)