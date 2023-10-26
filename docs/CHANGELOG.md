# Changelog

## 4.4

_Released 26/10/2023_

### 🐞 Bug fixes

- [Cocoa] Window not retaining focus on keystrokes. #1187
- [Cocoa] App crashing when closing fullscreen window. #1236
- [Cocoa] Video keeps playing after closing window. #1235
- [Cocoa] Uploaded file is empty if filename contains a space. #1231
- [Cocoa] Return value of confirmation dialog created by `window.confirm`. #976
- [Windows] Fullscreen application disappearing after disconnecting extended display. #1229

### 🚀 Improvements

- [All] Don't start http server for file:// urls. Thanks @glorpen
- [GTK] Bump WebKit2 to 4.1. Thanks @starnight
- [Windows] Disable swipe navigation #1230
- [Windows] Window is changed to fullscreen on the current monitor in a multi-monitor setup.

## 4.3.3

_Released 08/09/2023_

### 🐞 Bug fixes

- [QT] Fix QT implementation

## 4.3.2

_Released 01/09/2023_

### 🐞 Bug fixes

- [Winforms] Fix `easy_drag` from being always enabled.

## 4.3.1

_Released 30/08/2023_

### 🐞 Bug fixes

- [Cocoa] Add missing maximized implementation

## 4.3

_Released 30/08/2023_

### ⚡ Features

- [All] `webview.create_window(maximized=False)` Create a window in a maximized state. Thanks @vsajip
- [All] `webview.create_window(screen=screen_instance)` Create a window on a specific monitor, where `screen` is a screen returned by `window.screens`. Thanks @louisnw01
- [All] Window title can be obtained / set via `window.title`.

### 🚀 Improvements

- [All] Window closing event fired after closing confirmation #1178. Thanks @p4bl0-
- [All] Improve performance of JS API calls by removing the initial delay of 100ms.
- [GTK] Native JS Bridge. HTTP server based JS bridge is removed.
- [GTK] Remove support for Webkit older than 2.2

### 🐞 Bug fixes

- [All] Easy drag memory leak #1176
- [Winforms] Easy drag support #1125
- [Winforms] Incorrect DPI scaling
- [Winforms] Private mode not working if `webview.screens` is returned before `webview.start` #1193
- [QT] Add no sandbox for arch/manjaro/nixos to avoid white screen problem #890. Thanks @myuanz
- [GTK] Closing event handlers cancellation. Thanks @p4bl0-
- [GTK] SEGFAULT on second `webview.start()` call #1063. Thanks @PercentBoat4164

## 4.2.2

_Released 25/06/2023_

- [All] Fix 'NoneType' object has no attribute 'start_server'. #1159

## 4.2.1

_Released 22/06/2023_

- [All] Fix installation

## 4.2

_Released 22/06/2023_

### ⚡ Features

- [All] `webview.create_window(focus=False)` to create a non-focusable window. Thanks @mi4code #1030.

### 🚀 Improvements

- [All] Modernization of project infrastructure + typing. Thanks @demberto.
- [Winforms] Top level menu item support. Thanks @zhengxiaoyao0716.
- [Winforms] Disable touchpad elastic overscroll. Thanks @firai.

### 🐞 Bug fixes

- [Winforms] Unable to load DLL 'WebView2Loader.dll': The specified module could not be found. Thanks @kawana77b #1078
- [Cocoa] Fix missing pip dependency `pyobjc-framework-security`.

## 4.1

_Released 02/05/2023_

### ⚡ Features

- [Cocoa/QT/GTK] SSL support for built-in http server  `webview.start(ssl=True)`. Thanks @keredson

### 🚀 Improvements

- [All] JS API exceptions are now printed both in Python and Javascript consoles.
- [All] Hide menu bar when there is no menu. Thanks @Joffreybvn

### ⚡ Features

- [All] Fix bug where http_port was not being forwarded to the actual window #1060. Thanks @robb-brown
- [All] Switch from tempfile to os.devnull to fix PyInstaller issue. Thanks @simonrob
- [Cocoa] Fix getting cookies in cocoa. Thanks @eerimoq
- [Cocoa] Fix exception occurring when main menu for application cannot be obtained.
- [Windows] A more robust logic for setting user data directory. Thanks @al-eax
- [Windows] Fix exception when executing a menu function
- [Windows] Fix the title and message of the confirmation dialog. Thanks @zhengxiaoyao0716

## 4.0.2

_Released 21/02/2023_

### 🚀 Improvements
- [All] HTTP server is now multithreaded. This should prevent stalled requests. #1025
- [Windows] `webview.start(storage_path)` can now be set in private mode. This can be useful if you do not have write access to EdgeChromium default data directory and get 0x80070005 (E_ACCESSDENIED) error. #1026

### 🐞 Bug fixes
- [All] Fix `AttributeError: module 'webview.http' has no attribute 'running'` exception occurring when multiple windows are opened. Thanks @YidaozhanYa. #1024
- [Winforms] Fix on_top not having any effect on Windows. #1036
- [Winforms] Fix `create_window(hidden=True)` makes the show() command not work #1050
- [Windows] Fix pyinstaller compatibility on Windows. Thanks @simonrob #1044
- [CEF] Fix window.get_cookies() throwing KeyError exception. #1021
- [Cocoa] Fix non-QWERTY keyboard shortcuts. Thanks @max-uho
- [QT] Fix web inspector preventing to open. #1028
- [GTK] Fix "ImportError: Requiring namespace 'Soup' version '2.4', but '3.0' is already loaded" Thanks @YidaozhanYa #1041


## 4.0.1

_Released 19/01/2023_

### 🚀 Improvements
- [All] Suppress HTTP server logging if not in debug mode.

### 🐞 Bug fixes
- [All] Fix HTTP server starting twice with a single window. Thanks @robb-brown.


## 4.0

_Released 18/01/2023_

### 💔 BREAKING CHANGES
- [All] Window events are moved into `window.events` namespace. `window.loaded`, `window.shown` etc no longer work.
- EdgeHTML support is removed.

### ⚡ Features
- [All] Local homegrown HTTP server is replaced with [bottle.py](https://bottlepy.org). Thanks @robb-brown for WSGI support.
- [All] Native application menu support. See `examples/menu.py` for usage example. Thanks @sardination
- [All] `webview.start(private_mode=True, storage_path=None)` Private mode and persistant storage support in a non-private mode. Private mode is enabled by default.
- [All] `webview.create_window(zoomable=False)` Enable / disable zooming on webpage. Disabled by default.
- [All] `webview.create_window(draggable=False)` Enable / disable dragging of IMG and A elements. Disabled by default.
- [All] `webview.create_confirmation_dialog(title, content)` creates a confirmation (Ok, Cancel) dialog. Thanks @sardination.
- [All] `window.get_cookies()` retrieve all the cookies (including HttpOnly) for the current webpage.
- [macOS] `webview.create_window(vibancy=False)` Window vibrancy suppport. macOS only. Thanks @CahierX.

### 🚀 Improvements
- [All] Local relative URLs (eg. src/index.html) are opened using the built-in http server by default. Support for local URLs is still possible using file:// schema
- [Cocoa] Disable Ctrl+click context menu. Thanks @ecpost.
- [EdgeChromium] Improve `evaluate_js` performance.
- [GTK] Enable media / audio / WebGL / clipboard related WebKit features

### 🐞 Bug fixes
- [Cocoa] Fix passing through keyboard events handled by pywebview. Thanks @ecpost.
- [GTK] Fix JS bridge maximum return object size limitation. GTK's JS bridge is implemented via HTTP server.
- [GTK] Fix hanging problem during window closing when JS evaluation is in progress


## 3.7.1

_Released 14/11/2022_

### 🐞 Bug fixes
- [Edge Chromium] Better platform detection

### 🚀 Improvements
- [Edge Chromium] ARM64 support

## 3.7

_Released 04/11/2022_

### ⚡ Features
- [All] New `window.events.moved` event. Thanks @irtimir

### 🚀 Improvements
- [EdgeChromium] Remove `The system cannot find the file specified - Microsoft Edge WebView2 Runtime Registry path: Computer\HKEY_CURRENT_USER\Microsoft\EdgeUpdate\Clients{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}` error message displayed in debug mode.
- [CEF] error.log is no longer deleted when in debug mode.

### 🐞 Bug fixes
- [All] Fix `evaluate_js_async` crash and program termination prevention. Thanks @detritophage.
- [WinForms] Fix form initialization for pythonnet 3. Thanks @irtimir
- [CEF] Fix errorous script execution in `evaluate_js`, so that further script do not get stuck. Thanks @irtimir
- [CEF] Fix `master uid not found` error on startup.
- [QT] Remove 'Empty key passed' messages. Thanks @TomFryers
- [QT] PySide6 backend not working. Thanks @sbbosco
- [QT] Prevent  'Release of profile requested but WebEnginePage still not deleted. Expect troubles !' message on close. Thanks @sbbosco


## 3.6.3

_Released 05/04/2022_
### 🐞 Bug fixes

- [Winforms] Support for Edge Chromium v100. Thanks @greper.

## 3.6.2

_Released 05/03/2022_
### 🐞 Bug fixes

- [Cocoa] Fix closing window

## 3.6.1

_Released 16/02/2022_
- `Fix` [CEF] Exception on start


## 3.6

_Released 15/02/2022_
- `New` [All] Python 3.6 is the minimum supported version from now on.
- `New` [All] `minimized`, `maximized`, `restored`, `resized` events. Thanks @BillBridge for sponsorship.
- `New` [All] `evaluate_js` async support. `evaluate_js(code, callback)` can evaluate promises via an optional callback parameter.
- `New` [All] Events moved to its own `window.events` namespace (e.g. `window.loaded` → `window.events.loaded`). Old events are supported throughout 3.x and will be removed in 4.0.
- `New` [All] `window.resize(width, height, fix_point)` has now an optional parameter fix_point that controls in respect to which point the window is resized.
- `New` [All] MSHTML and EdgeHTML are deprecated. No further development will be done on these renderers.
- `New` [Winforms] Focus webview on start or window activate events.
- `New` [EdgeChromium] Custom user agent support.
- `New` [EdgeChromium] Window transparency support. Mouse and keyboards events are not supported in transparent. Thanks @odtian.
- `New` [CEF] Ability to pass custom CEF browser settings. Thanks @Rolf-MP.
- `Improvement` [EdgeChromium] Support non-elevated installations of WebView2. Thanks @ultrararetoad.
- `Improvement` [EdgeChromium] Better support for Edge Chromium runtime detectiom. Thanks @r-muthu-saravanan.
- `Improvement` [EdgeChromium] WebView2 runtime updated to
- `Improvement` [QT] Pyside support via PyQT wrapper. Thanks @tshemeng.
- `Fix` [Cocoa] Make Ctrl-C (SIGINT) work on Cocoa when running from the command line
- `Fix` [EdgeChromium] Fix `load_html. Thanks @sbbosco.
- `Fix` [Cocoa] Fix cancelling of closing the window in the closing event Thanks @fizzadar.
- `Fix` [QT] Fix simultaneous calls to JS API.
- `Fix` [GTK] Fix concurrency issues with get_size, get_position and get_current_url.

## 3.5

_Released 02/08/2021_
- `New` [All] Get information about available screens via new `webview.screens` property.
- `New` [All] Per window localization. Thanks @fizzadar.
- `New` [All] Window closing can be cancelled by returning False from a closing event handler. #744.
- `Fix` [All] Debug mode cannot be set under certain conditions. #628
- `Improvement` [All] Selected web renderer printed in Python console in debug mode.
- `Improvement` [All] JS API serialization logic. Thanks @peter23
- `Improvement` [EdgeChromium] Chromium runtime updated to version 1.0.774.44. Thanks @sbbosco.
- `Improvement` [EdgeChromium] Custom user agent support.
- `Fix` [WinForms] Icon handling logic to make pywebview compatible with pystray. #720. Thanks @simonrob
- `Fix` [EdgeChromium] Change webview component to transparent. Thanks @ODtian
- `Fix` [CEF] Fix exception when destroying window
- `Fix` [Cocoa] cmd+w bypasses exit confirmation dialogue. #698. Thanks @fizzadar
- `Fix` [Cocoa] Fix window coordinate calculation logic when moving a window.
- `Fix` [MSHTML] Fix drag_region
- `Fix` [MSHTML] Fix window.alert


## 3.4: Second wave

_Released 04/12/2020_

- `New` [Windows] WebView2 Chromium support. Thanks [sbbosco](https://github.com/sbbosco). [#521](https://github.com/r0x0r/pywebview/issues/521).
- `Fix` [All] Exception with HTML checkboxes and `get_elements`. [#622](https://github.com/r0x0r/pywebview/issues/622).
- `Fix` [All] pystray compatibility. Thanks [AlexCovizzi](https://github.com/AlexCovizzi). [#486](https://github.com/r0x0r/pywebview/issues/486).
- `Fix` [All] expose methods instead of all callables for JS API objects. Thanks [jgentil](https://github.com/jgentil). [#629](https://github.com/r0x0r/pywebview/issues/629).
- `Fix` [EdgeHTML] Make returning results of `evaluate_js` more robust. Thanks [sbbosco](https://github.com/sbbosco).
- `Fix` [QT] KDE_FULL_SESSION not being used. Thanks [Maltzur](https://github.com/Maltzur).
- `Fix` [Cocoa] Unicode filenames for input files.
- `Improvement` [Cocoa] Only install the specific `pyobjc` packages required. Thanks [Fizzadar](https://github.com/fizzadar).
- `Improvement` [Cocoa] Add support for default document navigation and window handling shortcut keys . Thanks [ikhmyz](https://github.com/ikhmyz) and [Fizzadar](https://github.com/fizzadar)

## 3.3.5

_Released 26/09/2020_

- `Fix` [EdgeHTML] Server middleware handling
- `Fix` [EdgeHTML] file:// url handling

## 3.3.4

_Released 18/09/2020_

- `Fix` [EdgeHTML] Fix content not displaying with local URLs or local HTTP server
- `Fix` [Cocoa] Fixes arrow keys not responding in text input fields. Thanks [awesomo4000](https://github.com/awesomo4000)

## 3.3.3

_Released 08/08/2020_

- `Fix` [Cocoa] Save dialog not working [#578](https://github.com/r0x0r/pywebview/issues/578).
- `Fix` [Cocoa] Error sound being played when pressing keys on macOS [#566](https://github.com/r0x0r/pywebview/issues/566).

## 3.3.2

_Released 28/07/2020_

- `Fix` [All] Load html triggers error - resolve_url() missing 1 required positional argument: 'should_serve' [#562](https://github.com/r0x0r/pywebview/issues/562).
- `Fix` [Cocoa/GTK] Access window size on closing [#573](https://github.com/r0x0r/pywebview/issues/573).
- `Fix` [GTK] Save file dialog now returns a string instead of a tuple.

## 3.3.1

_Released 01/07/2020_

- `Fix` [WinForms] TypeError : 'str' value cannot be converted to System.Drawing.Color [#560](https://github.com/r0x0r/pywebview/issues/560).


## 3.3: Detroit Edition

_Released 29/06/2020_

- `New` [All] Brand-new WSGI based internal HTTP server. Thanks [@astronouth7303](https://github.com/astronouth7303).
- `New` [All] Transparent window. Not available on Windows.
- `New` [All] Allow _pywebview_ window to be on top of other windows.
- `New` [All] Custom window drag region using CSS classes. Thanks [@Fizzadar](https://github.com/Fizzadar).
- `New` [All] Custom user-agent support. Thanks [@tognee](https://github.com/tognee).
- `Fix` [All] Python function not triggered using JS [#458](https://github.com/r0x0r/pywebview/issues/458).
- `Fix` [All] window methods do not work in `loaded` event [#528](https://github.com/r0x0r/pywebview/issues/528).
- `Fix` [Cocoa] Caption bar and window control buttons are now hidden in frameless mode.
- `Fix` [CEF] CEF window resize hang [#484](https://github.com/r0x0r/pywebview/issues/484).
- `Fix` [MSHTML] Fix easy drag in frameless mode.
- `Fix` [EdgeHTML] Do not show admin prompt for non-local URLs.
- `Fix` [GTK] Fix threading issues with recentish versions of PyGObject
- `Fix` [QT] Fix opening web inspecting in debug mode

## 3.2: Humate Edition

_Released 24/01/2020_

- `New` [All] Window x, y, width and height properties to retrieve coordinates and dimensions of the window. Thanks [@Fizzadar](https://github.com/Fizzadar)
- `New` [All] `window.expose(func)` an ability to expose an arbitrary function to the JS realm, also during the runtime.
- `Improvement` [All] JS API methods can now accept an arbitrary number of arguments
- `Improvement` [All] Exceptions thrown in a JS API method is now raised in Javascript via its promise.
- `Improvement` [All] Exceptions thrown in window event handlers are now caught and logged.
- `Improvement` [All] Random port assigned by the built-in HTTP server can be retrieved via `webview.http_server.port`
- `Improvement` [QT] Microphone/webcam are enabled by default. Thanks [@dtcooper](https://github.com/dtcooper)
- `Improvement` [QT] Default debugger port is changed to 8228. Thanks [@melvinkcx](https://github.com/melvinkcx)
- `Improvement` [CEF] Ability to pass custom CEF settings via ` webview.platforms.cef.settings`. See [example](/examples/cef.md) for details.
- `Fix` [All] Built-in HTTP server is properly restarted when using `window.load_url`
- `Fix` [Cocoa] New window position is correctly calculated when using `window.move`
- `Fix` [EdgeHTML] `window.alert` fix


## 3.1: Windows Edition

_Released 04/11/2019_

- `New` [All] Window minimize/restore functionality. Ability to show window minimized on startup.
- `New` [All] Window hide/show functionality. Ability to show window hidden on startup.
- `New` [All] Window move functionality. Ability to set window coordinates on startup. Thanks @adbenitez.
- `New` [All] New `window.pywebviewready`DOM event that is thrown when `window.pywebview` is available.
- `New` [All] Links opened via `window.open` are opened in a new browser window.
- `Fix` [All] Fix concurrent invocations of JS API functions.
- `Fix` [All] Fix unescaped single quote in JS API calls.
- `Fix` [All] Built-in HTTP server is now multi-threaded. This fixes stalling HTTP requests in some cases.
- `Improvement` [All] `window.set_window_size` is deprecated in favour to `window.resize`.
- `Improvement` [All] Exceptions are now handled in JS API functions and rerouted to the function promise catch method.
- `Improvement` [All] Suppress built-in HTTP server logging. Logging is active only in the debug mode.
- `Fix` [CEF] Fix deadlock occurring when trying to access `window.pywebview` object right after the window is created.
- `Fix` [CEF] High DPI fix resulting in a small window appearing inside the main window,
- `Fix` [EdgeHTML] Unicode error when loading HTML.
- `Fix` [MSHTML] `get_elements` failing.
- `Fix` [MSHTML] `console.log` not writing to Python console in debug mode.
- `Fix` [MSHTML] Forcing MSHTML via `gui=mshtml` is now possible. ¯\\\_(ツ)\_/¯

<img src='/windows31.png' alt='Windows 3.1'/>


## 3.0.2

_Released 17/08/2019_

- `Fix` [All] Prevent JSON like strings being converted to JSON objects when returning JS API calls. #352
- `Fix` [Windows] HTTP server is now used by default for local URLs and HTML for EdgeHTML. This fixes a PermissionDenied error, when the directory the executable is in is not writable.
- `Fix` [Tests] Tests now fail on an exception occurring in a thread.


## 3.0.1

_Released 25/07/2019_

- `Fix` [All] Don't escape line breaks in result of js_bridge_call. Thanks @kvasserman.
- `Fix` [Windows] Support for Pyinstaller noconsole mode
- `Fix` [Windows] Fix Windows version detection with frozen executables.
- `Fix` [Windows] Open folder dialog now supports `directory` argument.
- `Fix` [QT] Workaround for segmentation fault on closing the main window. Thanks @kvasserman.
- `Fix` [Pytest] Fix for pytest warning about invalid escape sequence


## 3.0

_Released 11/07/2019_

- `New` [All] New API. The API is not compatible with older versions of _pywebview_. See https://pywebview.flowrl.com for usage details. #272
- `New` [All] Built-in HTTP server. #260
- `New` [All] Autogenerated CSRF token exposed as `window.pywebview.token`. #316
- `New` [All] `get_elements` function to retrieve DOM nodes. #292
- `New` [All] New events system that lets you to subscribe to events. `loaded` and `shown` events are implemented. #201
- `New` [Windows] EdgeHTML support. Thanks @heavenvolkoff. #243
- `Fix` [Windows] Fullscreen mode. #338
- `Fix` [GTK] Better Javascript support for recent version of WebKit2
- `Fix` [CEF] Support for PyInstaller in onefile mode


## 2.4

_Released 17/02/2019_

- `New` [All] Support for frameless windows.
- `Fix` [Windows] Fix broken installation of v2.3

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
- `Fix` [QT] Deprecate QT4. Starting from this version new features won't be tested on QT4 and support will be removed in the future.



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
