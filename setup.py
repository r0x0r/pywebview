import os
import platform
from setuptools import setup

if platform.system() == "Windows":
    extras_require = {
        'win32': ['pywin32', 'comtypes'],
        'winforms': ['pythonnet'],
    }
elif platform.system() == "Darwin":
    extras_require = {
        'cocoa': ['pyobjc'],
        'qt5': ['PyQt5'],
    }
elif platform.system() == "Linux":
    extras_require = {
        'gtk3': ['PyGObject'],
        'qt5': ['PyQt5'],
    }

setup(
    name="pywebview",
    author="Roman Sirokov",
    author_email="roman@flowrl.com",
    description=("A cross-platform lightweight native wrapper around a web view component"),
    url="http://github.com/r0x0r/pywebview",
    download_url="https://github.com/r0x0r/pywebview/archive/1.4.tar.gz",
    keywords=["gui", "webkit", "html", "web"],
    extras_require=extras_require,
    version="1.4",
    packages=["webview",],
    license="New BSD license",
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Environment :: MacOS X",
        "Environment :: Win32 (MS Windows)",
        "Environment :: X11 Applications :: GTK",
        "Environment :: X11 Applications :: Qt",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: User Interfaces"
        ],
)
