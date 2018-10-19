<p align='center'><img src='logo/logo.png' width=480 alt='pywebview logo'/></p>

<p align='center'><a href="https://badge.fury.io/py/pywebview"><img src="https://badge.fury.io/py/pywebview.svg" alt="PyPI version" /></a> <a href="https://travis-ci.org/r0x0r/pywebview"><img src="https://travis-ci.org/r0x0r/pywebview.svg?branch=master" alt="Build Status" /></a> <a href="https://ci.appveyor.com/project/r0x0r/pywebview"><img src="https://ci.appveyor.com/api/projects/status/nu6mbhvbq03wudxd?svg=true" alt="Build status" /></a></p>


pywebview is a lightweight cross-platform wrapper around a webview component that allows to display HTML content in its own native GUI window. It gives you power of web technologies in your desktop application, hiding the fact that GUI is browser based. You can use pywebview either with a lightweight web framework like [Flask](http://flask.pocoo.org/) or [Bottle](http://bottlepy.org/docs/dev/index.html) or on its own with a two way bridge between Python and DOM.

pywebview uses native GUI for creating a web component window: WinForms on Windows, Cocoa on Mac OSX and Qt4/5 or GTK3 on Linux. If you choose to freeze your application, pywebview does not bundle a heavy GUI toolkit or web renderer with it keeping the executable size small. Compatible with both Python 2 and 3. While Android is not supported, you can use the same codebase with solutions like [Python for Android](https://github.com/kivy/python-for-android) for creating an APK.

Licensed under the BSD license. Maintained by [Roman Sirokov](https://github.com/r0x0r/) and [Shiva Prasad](https://github.com/shivaprsdv).

# Supporting pywebview

pywebview is a BSD licensed open source project. It is an independent project with no corporate backing. If you find it useful, consider supporting it.

<a href="https://www.patreon.com/bePatron?u=13226105" data-patreon-widget-type="become-patron-button"><img src='https://c5.patreon.com/external/logo/become_a_patron_button.png' alt='Become a Patron!'/></a>

# Gallery

Apps created with pywebview. If you have built an app using pywebview, please do not hesitate to showcase it.

* Next for Traktor: http://flowrl.com/next
* Traktor Librarian: http://flowrl.com/librarian/

# Installation

If you have the [dependencies](#dependencies) installed, simply:

    pip install pywebview

To automatically fetch and install Python dependencies for your platform, install with the appropriate ["install extras"](http://setuptools.readthedocs.io/en/latest/setuptools.html#declaring-extras-optional-features-with-their-own-dependencies).

(Note that the same code is installed regardless; if more than one of the libraries below are available they will be tried in the order listed in this readme.)

On Windows (using WinForms with `pythonnet`):

    pip install pywebview[winforms]

On Mac (using the Cocoa WebKit widget via `pyobjc`):

    pip install pywebview[cocoa]

On Linux (using GTK3 via `PyGObject`):

    pip install pywebview[gtk3]

On Linux or Mac with either Qt 5:

    pip install pywebview[qt5]  # Qt5 with PyQt5

To use pywebview with PyQt4, you have to install it separately, as it is not available in pypi.

A second implementation for Windows using `pywin32` and `comtypes` is also available:

    pip install pywebview[win32]

# Dependencies

## Windows

On Windows you can choose between Win32 and Windows Forms implementation. The Win32 implementation is not actively developed and misses some features.

For Windows Forms
`pythonnet`

For Win32 you need
`pywin32`, `comtypes`. ActiveState distribution of Python 2 comes with pywin32 preinstalled


## macOS

`pyobjc`. PyObjC comes presintalled with the Python bundled in macOS. For a stand-alone Python installation you have to install it separately. QT is supported as well.


## Linux

For GTK3 based systems:`PyGObject`
On Debian based systems run
`sudo apt-get install python-gi gir1.2-webkit-3.0`

For QT based systems

Either `PyQt5` or `PyQt4`. PyQt4 is deprecated and will be removed in the future.

GTK has a preference over QT, except on KDE systems.


To force a GUI library, use `PYWEBVIEW_GUI` environment variable or set `webview.config.gui` variable. Possible values are `qt`, `gtk` or `win32`.


# Usage

    import webview
    webview.create_window("It works, Jim!", "http://pywebview.flowrl.com")

For more detailed usage, refer to the examples in the `examples` directory. There are three ways to build your app

1) Open a web page as in the example above. The page can be either local (`file://`) or remote. Using `file://` urls won't work
   with application is frozen
2) Use a relative url to load your application and provide a js_api object for Python-JS intercommunication. The URL is resolved
   automatically to work in a frozen environment as well. See `examples/todos`.
3) Run a local web server and point pywebview to display it. There is an example Flask application in the `examples/flask_app`
   directory. 

