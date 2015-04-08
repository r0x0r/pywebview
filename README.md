# pywebview

pywebview is a lightweight cross-platform wrapper around a webview component that allows to display HTML content in its own dedicated window. It gives you richness of web technologies in your desktop application, all without a need to resort to an external browser. Combined with a lightweight web framework like [Flask](http://flask.pocoo.org/), [Bottle](http://bottlepy.org/docs/dev/index.html) or [web.py](http://webpy.org), you can create beautiful cross-platform HTML5 user interfaces targeting WebKit, while hiding the implementation details from the end user.

pywebview is lightweight with no dependencies on external GUI framwork. It uses native GUI for creating a web component window: Win32 on Windows, Cocoa on Mac OSX and Qt4/5 or GTK3 on Linux. If you decide to convert your application to an executable format, it does not bundle a heavy GUI toolkit with it, which keeps the size of the executable small. Python 2 and 3 compatible.


# License

The BSD license



# Installation

    pip install pywebview


# Dependencies

## Windows

`comtypes`

## OS X 

`pyobjc`. It comes bundled with the python presinstalled in OS X. For Python 3 you have to install it separately.

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


# What web renderer is used?

For OS X and Linux systems you get WebKit. The actual version depends on the version of installed Safari on OS X and QT / GTK on Linux. Note that WebKit bundled with QT / GTK is slightly out of date comparing to the latest Safari or Chrome.

For Windows, you get, well, MSHTML (Trident) in all its glory. The version depends on the installed version of Internet Explorer. By default, when creating an embedded web component, MSHTML uses IE7 rendering mode. To overcome this feature, a registry setting is automatically modified to use the renderer of the latest installed version of Internet Explorer. Note that for Windows XP systems, you cannot get anything better than IE8. For Vista, you are limited to IE9.

Support for Chromium Embedded Framework (CEF) is planned for future versions.




# Changelog

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
