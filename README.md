# pywebview

pywebview is a lightweight cross-platform wrapper around a webview component that allows to display HTML content in its own native GUI window. It gives you power of web technologies in your desktop application, eliminating the need of launching a web browser. Combined with a lightweight web framework like [Flask](http://flask.pocoo.org/), [Bottle](http://bottlepy.org/docs/dev/index.html) or [web.py](http://webpy.org), you can create beautiful cross-platform HTML5 user interfaces targeting WebKit, while hiding implementation details from the end user. If HTML is not your strong point, you might want to use [REMI](https://github.com/dddomodossola/remi), which allows you to create HTML based interfaces using Python code only.

pywebview is lightweight and has no dependencies on an external GUI framework. It uses native GUI for creating a web component window: WinForms on Windows, Cocoa on Mac OSX and Qt4/5 or GTK3 on Linux. If you choose to freeze your application, it does not bundle a heavy GUI toolkit with it keeping the executable size small. Compatible with both Python 2 and 3. While Android is not supported, you can use the same codebase with solutions like [Python for Android](https://github.com/kivy/python-for-android) for creating an APK.


# License

The BSD license


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

- `webview.create_window(title, url="", width=800, height=600, resizable=True, fullscreen=False, min_size=(200, 100)), strings={}, confirm_quit=False)`
	Create a new WebView window. Calling this function will block application execution, so you have to execute your
	program logic in a separate thread.
	`strings` is a dictionary with localized strings that overwrites default strings. Localized strings are defined in localization.py

- `webview.load_url(url)`
	Load a new URL in the previously created WebView window. This function must be invoked after WebView windows is created with create_window(). Otherwise an exception is thrown.

- `webview.load_html(content)`
    Loads HTML content in the WebView window

- `webview.get_current_url()`
    Return a current URL
    
- `webview.toggle_fullscreen()`
    Toggle a fullscreen mode on the active monitor    
    
- `webview.create_file_dialog(dialog_type=OPEN_DIALOG, directory='', allow_multiple=False, save_filename='')`
    Create an open file (`webview.OPEN_DIALOG`), open folder (`webview.FOLDER_DIALOG`) or save file (`webview.SAVE_DIALOG`) dialog. `allow_multiple=True` enables multiple selection. `directory` Initial directory. `save_filename` Default filename for save file dialog.
    Return a tuple of selected files, None if cancelled

- `webview.destroy_window()`
    Destroy the webview window


# What web renderer is used?

For OS X and Linux systems you get WebKit. The actual version depends on the version of installed Safari on OS X and QT / GTK on Linux. 

For Windows, you get MSHTML (Trident) in all its glory. The version depends on the installed version of Internet Explorer. For Windows XP systems, you cannot get anything better than IE8. For Vista, you are limited to IE9. For Windows 7/8/10, you will get the latest installed version. Embedding EdgeHTML engine is not made possible by Microsoft. 


# How do I freeze my application?

Use py2app on OS X and pyinstaller on Windows. For reference setup.py files, look in `examples/py2app_setup.py`. Pyinstaller builds a working executable out of the box, however you might need to Python.Runtime.dll (of pythonnet) to the target directory.

# VirtualEnv issues 
Under virtualenv on OS X, a window created with pywebview has issues with keyboard focus and Cmd+Tab. This behaviour is caused by the Python interpretor that comes with virtualenv. To solve this issue, you need to overwrite `your_venv/bin/python` with the Python interpretor found on your system. Alternatively you can configure your virtual environment to use another Python interpretor as described [here](https://virtualenv.pypa.io/en/stable/userguide/#using-virtualenv-without-bin-python).
