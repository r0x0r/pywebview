# pywebview

pywebview is a lightweight cross-platform wrapper around a webview component that allows to display HTML content in its own dedicated window. It gives you richness of web technologies in your desktop application, all without a need to resort to an external browser. This way you can create beautiful cross-platform HTML5 user interfaces targeting WebKit, while hiding the implementation details from the end user.

pywebview is lightweight. It is one file affair with no dependencies other than those already provided by the operating system (PyObjC for Mac and PyQt4/5 for Linux). If you decide to convert your application to an executable format, it does not bundle a heavy GUI toolkit with it, which keeps the size of the executable in check.  pywebview relies on GUI toolkits built into a platform: Cocoa on Mac OSX and Qt4/5 on Linux. Windows is not supported at the moment, but it is on the to-do list.


# Installation

Place webview.py to your project directory and then import the module using

    import webview

That's it!


#Usage

    import webview
    
    webview.create_window("It works, Jim!", "http://www.flowrl.com")

For more elaborated usage, refer to the examples in the examples folder  



# Changelog

20/11/2014

Version 0.1
- First release
- Linux and OSX support