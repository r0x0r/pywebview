# pywebview

pywebview is a lightweight cross-platform wrapper around a webview component that allows to display HTML content in its own dedicated window. It gives you richness of web technologies in your desktop application, all without a need to resort to an external browser. Combined with a lightweight web framework like [Flask](http://flask.pocoo.org/), [Bottle])(http://bottlepy.org/docs/dev/index.html) or [web.py](http://webpy.org), you can create beautiful cross-platform HTML5 user interfaces targeting WebKit, while hiding the implementation details from the end user.

pywebview is lightweight. It is one file affair with no dependencies other than those already provided by the operating system (PyObjC for Mac and PyQt4/5 for Linux). If you decide to convert your application to an executable format, it does not bundle a heavy GUI toolkit with it, which keeps the size of the executable in check.  pywebview relies on GUI toolkits built into a platform: Cocoa on Mac OSX and Qt4/5 on Linux. Windows is not supported at the moment, but it is on the to-do list. Python 2 and 3 compatible.


# Installation

Place webview.py to your project directory and then import the module using

    import webview

That's it!


#Usage

    import webview
    
    webview.create_window("It works, Jim!", "http://www.flowrl.com")

For more elaborated usage, refer to the examples in the examples folder  


# API

- `webview.create_window(title, url, width=800, height=600, resizable=True)`
	Create a new WebView window. Calling this function will block execution, so you have to execute your program logic in a separate thread.



- `webview.load_url(url)`
	Load a new URL into a previously created WebView window. This function must be invoked after WebView windows is created with create_window(). Otherwise an exception is thrown.


# Changelog

20/11/2014

Version 0.1
- First release
- Linux and OSX support