# pywebview

pywebview is a lightweight cross-platform wrapper around a webview component that allows to display HTML content in its own native GUI window. It gives you power of web technologies in your desktop application, eliminating the need of launching a web browser. Combined with a lightweight web framework like [Flask](http://flask.pocoo.org/), [Bottle](http://bottlepy.org/docs/dev/index.html) or [web.py](http://webpy.org), you can create beautiful cross-platform HTML5 user interfaces targeting WebKit, while hiding implementation details from the end user. If HTML is not your strong point, you might want to use [REMI](https://github.com/dddomodossola/remi), which allows you to create HTML based interfaces using Python code only.

pywebview is lightweight and has no dependencies on an external GUI framework. It uses native GUI for creating a web component window: Win32 on Windows, Cocoa on Mac OSX and Qt4/5 or GTK3 on Linux. If you choose to freeze your application, it does not bundle a heavy GUI toolkit with it keeping the executable size small. Compatible with both Python 2 and 3. While Android is not supported, you can use the same codebase with solutions like [Python for Android](https://github.com/kivy/python-for-android) for creating an APK.


# License

The BSD license


# Gallery

Apps created with pywebview. If you have built an app using pywebview, please do not hesitate to showcase it.

Next for Traktor: http://flowrl.com/next
Traktor Librarian: http://flowrl.com/librarian/


# Installation

    pip install pywebview


# Contributions and bug reports

Help, PRs and donations are welcome. If you found a bug, please test it first in a web-browser that is used by default for your operating system to see if the problem is with your code, rather than pywebview. Feature requests are welcome, but nothing is guaranteed. 

Donate with Paypal: http://bit.ly/2eg2Z5P


# Dependencies

## Windows

On Windows you can choose between Win32 and Windows Forms implementation.

For Win32 you need
`pywin32`, `comtypes`. ActiveState distribution of Python 2 comes with pywin32 preinstalled

For Windows Forms
`pythonnet`

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

- `webview.create_window(title, url="", width=800, height=600, resizable=True, fullscreen=False, min_size=(200, 100))`
	Create a new WebView window. Calling this function will block application execution, so you have to execute your
	program logic in a separate thread.

- `webview.load_url(url)`
	Load a new URL in the previously created WebView window. This function must be invoked after WebView windows is created with create_window(). Otherwise an exception is thrown.

- `webview.load_html(content)`
    Loads HTML content in the WebView window
    
- `webview.create_file_dialog(dialog_type=OPEN_DIALOG, directory='', allow_multiple=False, save_filename='')`
    Create an open file (`webview.OPEN_DIALOG`), open folder (`webview.FOLDER_DIALOG`) or save file (`webview.SAVE_DIALOG`) dialog. `allow_multiple=True` enables multiple selection. `directory` Initial directory. `save_filename` Default filename for save file dialog.
    Return a tuple of selected files, None if cancelled

- `webview.destroy_window()`
    Destroy a webview window


# What web renderer is used?

For OS X and Linux systems you get WebKit. The actual version depends on the version of installed Safari on OS X and QT / GTK on Linux. 

For Windows, you get MSHTML (Trident) in all its glory. The version depends on the installed version of Internet Explorer. For Windows XP systems, you cannot get anything better than IE8. For Vista, you are limited to IE9. For Windows 7/8/10, you will get the latest installed version. Embedding EdgeHTML engine in third party applications is not supported  by Microsoft at the moment. 


# How do I freeze my application?

Use py2app on OS X and py2exe/pyinstaller on Windows. For reference setup.py files, look in `examples/py2app_setup.py` and `examples/py2exe_setup.py`


# Changelog

## 1.3
Released 31/10/2016
- `New` [Cocoa] Added View -> Fullscreen standard menu item. Thanks to @bastula.
- `New` [Cocoa] Added About menu item #45. Thanks to @bastula.
- `New` [Windows] An application icon for Windows Forms
- `Fix` [Windows] Removed unnecessary pywin32 dependencies from Windows Forms #60
- `Fix` [Linux] Thread violation in load_url in GTK implementation #59


## 1.2.2
Released 10/10/2016

- `Fix` [All] Python 2 compatibility issue in Flask Example (#52). Thanks to @bastula.
- `Fix` [Windows] Python 3 compatibility issue in Windows Forms implementation (#51)
- `Fix` [Linux] Resizing width/height: 100% problem on GTK (#53). Thanks to @klausweiss. 


## 1.2.1
Released 29/09/2016

- `Fix` [Linux] GTK window failing to open. Thanks to @lchish. #50


## 1.2
Released 27/09/2016

- `New` [All] Introduced `load_html` function that allows dynamic loading of HTML code, instead of a URL. Implemented for all platforms except Win32 (use Windows Forms). Thanks to @ysobolev #39
- `New` [All]  Added an example of a Flask-based application skeleton. The example can be found in `examples/flask_app`
- `New` [Windows] Windows Forms based implementation of webview window. Requires pythonnet.
- `New` [Windows] Introduced config["USE_WIN32"] variable that lets you choose between Win32 and Windows Forms. Default to True (Windows Forms will be made as default in the future)
- `Fix` [Windows/Linux] Got rid of installation dependencies on Windows and Linux. The dependencies now have to be installed by hand and the choice of dependencies is left to user
- `Fix` [Linux] Compatibility with Qt 5.5. Thanks to @danidee10. #48


## 1.1
Released 08/06/2016

- `New` [OSX] Add a default application menu #35. Thanks @cuibonobo
- `New` [Linux] GTK is made as default and pypi dependency added. USE_GTK environment variable is also deprecated. To use QT, set `webview.config["USE_QT"] = True`
- `Fix` [Windows] Open folder of create_file_dialog now returns Unicode, instead of byte encoding.


## 1.0.2
Released 19/05/2016

- `Fix` [Windows] Fix a dead-lock that sometimes occurs on a window creation, when used with a HTTP server running in a separate thread.


## 1.0.1
Released 17/05/2016

- `Fix` [Windows] PyInstaller: Icon not found #29


## 1.0
Released 12/02/2016

- `New` [All] Add an ability to programmatically destroy a webview window
- `Fix` [Windows] Fullscreen mode
- `Fix` [Windows] Change setup.py to use pypiwin32 #22
- `Fix` [Windows] Relative import of win32_gen fixed on Python 3 #20. Thanks to @yoavram for the contribution
- `Fix` [Windows] FileNotFound exception on Windows 2003. Thanks to @jicho for the contribution
- `Fix` [OSX] Non-SSL URLs are allowed by default on El Capitan. Thanks to @cr0hn for the contribution


## 0.9
Released 27/11/2015

- `New` [All] Right click context menu is disabled #12
- `New` [All] Window minimum size constraints #13
- `New` [All] Save file dialog
- `New` [All] Added `directory` and `save_filename` parameters to `create_file_dialog`
- `New` [All] An option to set a default directory in a file dialog
- `New` [GTK] Introduced USE_GTK environment variable. When set, GTK is preferred over QT.
- `Fix` [Windows] Webview scrollbar sizing with a non-resizable window
- `Fix` [Windows] Add support for application icon #9
- `Fix` [Windows] Disable logging spam for comtypes


## 0.8.4

- `Fix` [Windows] Invisible scrollbars
- `Fix` [Windows] Fullscreen mode

## 0.8.3

- `Fixed` #10 Underlying browser does not resize with window under windows

## 0.8.2

Released on 08/10/2015

- `Fixed` Pressing close window button terminates the whole program on OSX

## 0.8

Released on 06/10/2015

- `New` Support for native open file / open folder dialogs
- `Fixed` #6 FEATURE_BROWSER_EMULATION not in winreg.HKEY_CURRENT_USER. Thanks to @frip for the fix.


## 0.7

Released on 08/04/2015

- `Fixed` Python 3 compatibility in Win32 module (thanks @Firnagzen) #3
- `Fixed` Floating values for window dimensions causing issues on Windows XP (thanks @Firnagzen) #4
- `Fixed` Correct IE version registry key on Windows XP (thanks @Firnagzen) #5

## 0.6

Released on 11/02/2015

- `Fixed` A problem preventing from creating a window on Windows

## 0.5

Released on 30/11/2014

- `New` Windows support
- `New` GTK3 support
- `New` pip installation
- `New` Fullscreen mode

## 0.1

Released on 20/11/2014

- First release
- Linux and OSX support
