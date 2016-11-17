


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
