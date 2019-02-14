


# Changelog

## 2.3

_Released 12/02/2019_

- `New` [All] Ability to resize window after creation `webview.set_window_size(width, height)`. Thanks @aprowe #274
- `New` [Windows] Chrome Embedded Framework (CEF) support #15
- `Improvement` [All] _pywebview_ does not interfer with Python's logger configuration #295
- `Fix` [All] Empty DOM issues when window is created without a URL #285
- `Improvement` [macOS] Web renderer upgraded to WKWebView
- `Improvement` [macOS] Add support for Mojave dark mode
- `Fix` [macOS] Problem with handling paths containing spaces #283
- `Fix` [QT] Better support for QTWebKit and QTWebChannel #304
- `Improvement` [QT] Remove support for QT4
- `Fix` [GTK] Thrown exception not Python 2 compatible #277


## 2.2.1

_Released 24/10/2018_

- `Fix` Dependency installation
- `New` Reintroduce [qt] extra require switch

## 2.2

_Released 23/10/2018_

- `New` Brand new documentation at https://pywebview.flowrl.com
- `Improvement` Simplify installation. Now pywebview can be installed by `pip install pywebview`. Dependencies will be resolved and installed automatically
- `Improvement` [GTK] Update to WebKit2

## 2.1

Released 16/09/2018

- `New` [All] Introduce `PYWEBVIEW_GUI` environment variable and `webview.config.gui` property. Acceptable values are are `qt`, `gtk` and `win32`. `USE_QT` and `USE_WIN32` is deprecated.
- `Fix` [Cocoa] Closing main window does not result in program termination
- `Fix` [All] New main window re-creation after closing. #229
- `Fix` [QT] Debug mode #233
- `Fix` [Cocoa/Windows] Preserve JS API on page reload
- `Fix` [Windows] `toggle_fullscreen()` function #232. Thanks @lt94
- `Fix` [Windows] `load_css()` function. Thanks @wormius.

## 2.0.3

Released 16/05/2018

- `Fix` [QT] Fix a deadlock preventing QT implementation from starting
- `Fix` [QT] QT is set to default on QT-based systems


## 2.0.1/2.0.2

Released 08/05/2018

- `Fix` [Winforms] Fix installation of dlls

## 2.0

Released 28/04/2018
- `New` [All] Multi-window support
- `New` [All] Ability to call Python code from Javascript via `window.pywebview.api`
- `New` [All] Debug mode. Web inspector for Cocoa/GTK/QT and basic debug information for WinForms.
- `New` [All] File filter support in `create_file_dialog`
- `New` [All] `target='_blank'` links are now opened in an external browser
- `New` [All] Change window title via a `set_title` function #159
- `New` [All] `load_css` function
- `New` [All] Support for relative local URLs in `create_window` / `load_html`. Linked local resources are resolved as well. #186
- `New` [All] `todos` example app demonstrating js api and relative local URLs.
- `New` [All] Text select in the webview window is disabled by default. Added `text_select` argument to `create_window` function.
- `New` [QT] OpenBSD 6.x support #213. Thanks @hucste.
- `Fix` [All] `base_uri` parameter of `load_html` defaults to the directory of the entry script
- `Fix` [All] Consistent return types with `evaluate_js` across different platforms #175
- `Fix` [All] Various concurrency issues and deadlocks
- `Fix` [Winforms] Hide `Message from webpage` when using `alert` Javascript function #150
- `Fix` [Winforms] Support for high DPI #179
- `Fix` [QT] Support for QT 5.10 #171. Thanks @adbenitez
- `Fix` [QT] Deprecate QT4. Starting from this verison new features won't be tested on QT4 and support will be removed in the future.



## 1.8
Released 29/10/2017
- pywebview has the official logo
- @shivaprsdv is now an official maintainer of the project
- `New` [All] Add an ability to run Javascript code using `evaluate_js` function
- `Fix` [Cocoa] Implement missing webview components (file input dialog, alert()/confirm() JS functions)
- `Fix` [Winforms] Fix issue with non-responsive UI when a loading screen background color is used
- `Fix` [Winforms] Add support for Del and Ctrl+A keys in input elements.
- `New` [QT] QT5 is now prefererred over QT4
- `Fix` [QT] Fix return parameters of `create_file_dialog` to have the same format as on other platforms
- `Fix` [GTK] Better threading model. Thanks to @jorants #121


## 1.7
Released 08/06/2017
- `New` [All] Add a basic test suite and continuous integration. #88
- `New` [All] Add a background_color parameter to create_window, which specifies the default color of the webview window. Refer to examples/loading_indicator.py for example use. Thanks to @shivaprsdv. #90
- `New` [Cocoa] Disable backspace navigation. Thanks to @shivaprsdv. #102
- `New` [Cocoa] Implementation of window.print() and window.confirm method. Thanks to @shivaprsdv. #97
- `Fix` [Cocoa] Fix non-existing localization string in save file dialog
- `New` [Winforms] Disable all the shortcut keys of web navigation
- `Fix` [Winforms] Fix load_html failing sometimes due thread violation
- `Fix` [GTK] Implement fall-through to QT, when GTK is present, but not GTK.WebKit.

## 1.6
Released 29/03/2017
- `New` [All] Quit confirmation dialog #31
- `New` [All] webview.config can be used using the dot notation (ie. webview.config.use_win32 = True)
- `New` [Winforms] Disable context menu
- `Fix` [Winforms] Application icon is now visible in the application window when frozen with PyInstaller #91
- `Fix` [Mac] load_html() is invoked as soon as the webview is ready #93
- `Fix` [QT] get_current_url() not working due a typo. Thanks @maroc81. #85
- `Fix` [GTK] Better exception handling when GTK is not found #94
- `Fix` [GTK] destroy_window() #95


## 1.5
Released 09/02/2017
- `New` [All] toggle_fullscreen function #52
- `New` [All] get_current_url function #76
- `New` [Winforms] Javascript errors are now suppressed
- `Fix` [Winforms] Fixed resizable=False not being enforced #73


## 1.4
Released 14/01/2017
- `New` [All] pip installation now supports choosing what dependencies to install. See README for more information. Thanks @josePhoenix
- `New` [All] Localization support. Refer to `examples/localization.py` for an example use
- `New` [Mac] QT5 support
- `Fix` [Windows] File dialogs are now attached to the main window
- `Fix` [Windows] Pyinstaller crash issue with an icon in Windows Forms


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
