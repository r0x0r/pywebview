<p align='center'><img src='logo/logo.png' width=480 alt='pywebview logo'/></p>

<p align='center'><a href="https://badge.fury.io/py/pywebview"><img src="https://badge.fury.io/py/pywebview.svg" alt="PyPI version" /></a> <a href="https://travis-ci.org/r0x0r/pywebview"><img src="https://travis-ci.org/r0x0r/pywebview.svg?branch=master" alt="Build Status" /></a> <a href="https://ci.appveyor.com/project/r0x0r/pywebview"><img src="https://ci.appveyor.com/api/projects/status/nu6mbhvbq03wudxd?svg=true" alt="Build status" /></a></p>


pywebview is a lightweight cross-platform wrapper around a webview component that allows to display HTML content in its own native GUI window. It gives you power of web technologies in your desktop application, hiding the fact that GUI is browser based. You can use pywebview either with a lightweight web framework like [Flask](http://flask.pocoo.org/) or [Bottle](http://bottlepy.org/docs/dev/index.html) or on its own with a two way bridge between Python and DOM.

pywebview uses native GUI for creating a web component window: WinForms on Windows, Cocoa on Mac OSX and Qt4/5 or GTK3 on Linux. If you choose to freeze your application, pywebview does not bundle a heavy GUI toolkit or web renderer with it keeping the executable size small. Compatible with both Python 2 and 3. While Android is not supported, you can use the same codebase with solutions like [Python for Android](https://github.com/kivy/python-for-android) for creating an APK.

Licensed under the BSD license. Maintained by [Roman Sirokov](https://github.com/r0x0r/) and [Shiva Prasad](https://github.com/shivaprsdv).


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


## OS X 

`pyobjc`. PyObjC comes presintalled with the Python bundled in OS X. For a stand-alone Python installation you have to install it separately.

## Linux

For GTK3 based systems:`PyGObject`
On Debian based systems run
`sudo apt-get install python-gi gir1.2-webkit-3.0`

For QT based systems

Either `PyQt4` or `PyQt5`


# Usage

    import webview
    
    webview.create_window("It works, Jim!", "http://www.flowrl.com")

For more elaborated usage, refer to the examples in the `examples` directory.
There is also a sample Flask application boilerplate provided in the `examples/flask_app` directory. It provides
an application scaffold and boilerplate code for a real-world application.


## API

- `webview.create_window(title, url='', js_api=None, width=800, height=600, resizable=True, fullscreen=False,
                         min_size=(200, 100)), strings={}, confirm_quit=False, background_color='#FFF', debug=False)`
  
  Create a new WebView window. Calling this function for the first time will start the application and block program execution;
  so you have to execute your program logic in a separate thread. Subsequent calls will return a unique `uid` for the created
  window, which can be used to refer to the specific window in the API functions (single-window applications need not bother about
  the `uid` and can simply omit it from function calls; see below).
  * `title` - Window title
  * `url` - URL to load
  * `js_api` - Expose `js_api` to the DOM of the current WebView window. Callable functions of `js_api` can be executed
    using Javascript page via `window.pywebview.api` object. Custom functions accept a single parameter, either a
    primitive type or an object. Objects are converted to `dict` on the Python side. Functions are executed in separate
    threads and are not thread-safe.
  * `width` - Window width. Default is 800px.
  * `height` - Window height. Default is 600px.
  * `resizable` - Whether window can be resized. Default is True
  * `fullscreen` - Whether to start in fullscreen mode. Default is False
  * `min_size` - a (width, height) tuple that specifies a minimum window size. Default is 200x100
  * `strings` - a dictionary with localized strings. Default strings and their keys are defined in localization.py
  * `confirm_quit` - Whether to display a quit confirmation dialog. Default is False
  * `background_color` - Background color of the window displayed before WebView is loaded. Specified as a hex color. Default is white.
  * `debug` - (OSX only) Enables web inspector, when set to True.


These functions below must be invoked after atleast one WebView window is created with `create_window()`. Otherwise an exception is thrown.
In all cases, `uid` is the uid of the target window returned by `create_window()`; if no window exists with the given `uid`, an exception
is thrown. Default is `'master'`, which is the special uid given to the initial window.

- `webview.set_title(title, uid='master')`
    Change the window title.

- `webview.load_url(url, uid='master')`
    Load a new URL into the specified WebView window. 

- `webview.load_html(content, uid='master')`
    Loads HTML content into the specified WebView window.
    
- `webview.evaluate_js(script, uid='master')`
    Execute Javascript code in the specified window. The last evaluated expression is returned.

- `webview.get_current_url(uid='master')`
    Return the currently loaded URL in the specified window.
    
- `webview.toggle_fullscreen(uid='master')`
    Toggle fullscreen mode of a window on the active monitor.
    
- `webview.create_file_dialog(dialog_type=OPEN_DIALOG, directory='', allow_multiple=False, save_filename='', file_types=())`

  Create an open file (`webview.OPEN_DIALOG`), open folder (`webview.FOLDER_DIALOG`) or save file (`webview.SAVE_DIALOG`) dialog.
  Return a tuple of selected files, None if cancelled.
  * `allow_multiple=True` enables multiple selection.
  * `directory` Initial directory.
  * `save_filename` Default filename for save file dialog.
  * `file_types` A tuple of supported file type strings in the open file dialog. A file type string must follow this format `"Description (*.ext1;*.ext2...)"`.
  If the argument is not specified, then the `"All files (*.*)"` mask is used by default. The 'All files' string can be changed in the localization dictionary.

- `webview.destroy_window(uid='master')`
    Destroy the specified WebView window.

- `webview.window_exists(uid='master')`
    Return True if a WebView window with the given uid is up and running, False otherwise.


# Testing

pywebview uses [pytest](https://docs.pytest.org/en/latest/) for testing. To run tests, simply type `pytest tests` in the project root directory. Tests cover only trivial mistakes, syntax errors, exceptions and such, in other words there is no functional testing. Each test verifies that a pywebview window can be opened and exited without errors when run under different scenarios.


# What web renderer is used?

For OS X and Linux systems you get WebKit. The actual version depends on the version of installed Safari on OS X and QT / GTK on Linux. 

For Windows, you get MSHTML (Trident) in all its glory. The version depends on the installed version of Internet Explorer. For Windows XP systems, you cannot get anything better than IE8. For Vista, you are limited to IE9. For Windows 7/8/10, you will get the latest installed version. Embedding EdgeHTML engine is not made possible by Microsoft. 


# How do I freeze my application?

Use py2app on OS X and pyinstaller on Windows. For reference setup.py files, look in `examples/py2app_setup.py`. Pyinstaller builds a working executable out of the box, however you need to include .NET assembly Python.Runtime.dll (of pythonnet) to the target directory by providing built-in pyinstaller hook. The proper way to use this clr hook is to specify --hidden-import=clr from command-line or hiddenimports=['clr'] in spec file. This should take care of finding Python.Runtime.DLL hidden import for Windows.


# VirtualEnv issues 
Under virtualenv on OS X, a window created with pywebview has issues with keyboard focus and Cmd+Tab. This behaviour is caused by the Python interpretor that comes with virtualenv. To solve this issue, you need to overwrite `your_venv/bin/python` with the Python interpretor found on your system. Alternatively you can configure your virtual environment to use another Python interpretor as described [here](https://virtualenv.pypa.io/en/stable/userguide/#using-virtualenv-without-bin-python).
