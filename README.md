# pywebview

pywebview is a lightweight cross-platform wrapper around a webview component that allows to display HTML content in its own native GUI window. It gives you power of web technologies in your desktop application, eliminating the need of launching a web browser. Combined with a lightweight web framework like [Flask](http://flask.pocoo.org/), [Bottle](http://bottlepy.org/docs/dev/index.html) or [web.py](http://webpy.org), you can create beautiful cross-platform HTML5 user interfaces targeting WebKit, while hiding implementation details from the end user.

pywebview is lightweight and has no dependencies on an external GUI framework. It uses native GUI for creating a web component window: Win32 on Windows, Cocoa on Mac OSX and Qt4/5 or GTK3 on Linux. If you choose to freeze your application, it does not bundle a heavy GUI toolkit with it, which keeps the executable size small. Compatible with both Python 2 and 3.


# License

The BSD license



# Installation

    pip install pywebview


# Dependencies

## Windows

`pywin32`, `comtypes`. ActiveState distribution of Python 2 comes with pywin32 preinstalled

## OS X 

`pyobjc`. PyObjC comes presintalled with the Python bundled in OS X. For a stand-alone Python installation you have to install it separately.

## Linux

For GTK3 based systems
`PyGObject`

For QT based systems

Either `PyQt4` or `PyQt5`


# Usage

    import webview
    
    webview.create_window("It works, Jim!", "http://www.flowrl.com")

For more elaborated usage, refer to the examples in the examples folder  


## API

- `webview.create_window(title, url, width=800, height=600, resizable=True, fullscreen=False)`
	Create a new WebView window. Calling this function will block execution, so you have to execute your program logic in a separate thread.

- `webview.load_url(url)`
	Load a new URL into a previously created WebView window. This function must be invoked after WebView windows is created with create_window(). Otherwise an exception is thrown.

- `webview.create_file_dialog(dialog_type=OPEN_DIALOG, allow_multiple=False)`
    Create an open file (`webview.OPEN_DIALOG`) or open folder (`webview.FOLDER_DIALOG`) dialog. `allow_multiple=True` enables multiple selection. Return a tuple of selected files, None if cancelled


# What web renderer is used?

For OS X and Linux systems you get WebKit. The actual version depends on the version of installed Safari on OS X and QT / GTK on Linux. Note that WebKit bundled with QT / GTK is slightly out of date comparing to the latest Safari or Chrome.

For Windows, you get, well, MSHTML (Trident) in all its glory. The version depends on the installed version of Internet Explorer. By default, when creating an embedded web component, MSHTML uses IE7 rendering mode. To overcome this feature, a registry setting is modified to use the latest installed version of Internet Explorer. Note that for Windows XP systems, you cannot get anything better than IE8. For Vista, you are limited to IE9.

Support for Chromium Embedded Framework (CEF) is planned for future versions. Help with embedding CEF is welcomed.

# Cache issues

Web renderer might cache your code and fail to invalidate it, when it is updated. To prevent that add the following directives to the `<HEAD>` of your HTML files
    
    <meta http-equiv="pragma" content="no-cache">
    <meta http-equiv="cache-control" content="no-cache">
    <meta http-equiv="expires" content="-1">
    

# How do I freeze my application?

Use py2app on OS X and py2exe on Windows. For reference setup.py files, look in `examples/py2app_setup.py` and `examples\py2exe_setup.py`



# Changelog

## 0.9

- `New` Right click context menu is disabled

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
