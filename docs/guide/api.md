
# API

## webview.create_window

``` python
webview.create_window(title, url='', html='', js_api=None, width=800, height=600, \
                      x=None, y=None, resizable=True, fullscreen=False, \
                      min_size=(200, 100), hidden=False, frameless=False, \
                      minimized=False, on_top=False, confirm_close=False, \
                      background_color='#FFF', text_select=False)
```

Create a new _pywebview_ window and returns its instance. Window is not shown until the GUI loop is started. If the function is invoked during the GUI loop, the window is displayed immediately.

* `title` - Window title
* `url` - URL to load. If the URL does not have a protocol prefix, it is resolved as a path relative to the application entry point. Alternatively a WSGI server object can be passed to start a local web server.
* `html` - HTML code to load. If both URL and HTML are specified, HTML takes precedence.
* `js_api` - Expose a python object to the DOM of the current `pywebview` window. Methods of  the `js_api` object can be executed from Javascript by calling `window.pywebview.api.<methodname>(<parameters>)`. Please note that the calling Javascript function receives a promise that will contain the return value of the python function. Only basic Python objects (like int, str, dict, ...) can be returned to Javascript.
* `width` - Window width. Default is 800px.
* `height` - Window height. Default is 600px.
* `x` - Window x coordinate. Default is centered.
* `y` - Window y coordinate. Default is centered.
* `resizable` - Whether window can be resized. Default is True
* `fullscreen` - Start in fullscreen mode. Default is False
* `min_size` - a (width, height) tuple that specifies a minimum window size. Default is 200x100
* `hidden` - Create a window hidden by default. Default is False
* `frameless` - Create a frameless window. Default is False.
* `easy_drag` - Easy drag mode for frameless windows. Window can be moved by dragging any point. Default is True. Note that easy_drag has no effect with normal windows. To control dragging on an element basis, see [drag area](/guide/security.md#drag-area) for details.
* `minimized` - Start in minimized mode
* `on_top` - Set window to be always on top of other windows. Default is False.
* `confirm_close` - Whether to display a window close confirmation dialog. Default is False
* `background_color` - Background color of the window displayed before WebView is loaded. Specified as a hex color. Default is white.
* `transparent` - Create a transparent window. Not supported on Windows. Default is False. Note that this setting does not hide or make window chrome transparent. To hide window chrome set `frameless` to True.
* `text_select` - Enables document text selection. Default is False. To control text selection on per element basis, use [user-select](https://developer.mozilla.org/en-US/docs/Web/CSS/user-select) CSS property.

## webview.start

``` python
webview.start(func=None, args=None, localization={}, gui=None, debug=False, \
              http_server=False, user_agent=None)
```

Start a GUI loop and display previously created windows. This function must be called from a main thread.

* `func` - function to invoke upon starting the GUI loop.
* `args` - function arguments. Can be either a single value or a tuple of values.
* `localization` - a dictionary with localized strings. Default strings and their keys are defined in localization.py
* `gui` - force a specific GUI. Allowed values are `cef`, `qt` or `gtk` depending on a platform. See [Renderer](/guide/renderer.md) for details.
* `debug` - enable debug mode. See [Debugging](/guide/debugging.md) for details.
* `http_server` - enable built-in HTTP server. If enabled, local files will be served using a local HTTP server on a random port. For each window, a separate HTTP server is spawned. This option is ignored for non-local URLs.
* `user_agent` - change user agent string. Not supported in EdgeHTML.

### Examples
* [Simple window](/examples/open_url.html)
* [Multi-window](/examples/multiple_windows.html)

## webview.screens

``` python
webview.screens
```

Return a list of available displays (as `Screen` objects) with the primary display as the first element of the list.

### Examples
* [Simple window](/examples/screens.html)

## webview.token

``` python
webview.token
```

A CSRF token property unique to the session. The same token is exposed as `window.pywebview.token`. See [Security](/guide/security.md) for usage details.


# Screen object

Represents a display found on the system.


## height

``` python
screen.height
```

Get display height.

## width

``` python
screen.width
```

Get display width.

# Window object

Represents a window that hosts webview. `window` object is returned by `create_window` function.

## on_top

``` python
window.on_top
```

Get or set whether the window is always on top

## x
``` python
window.x
```
Get X coordinate of the top-left corrner of the window

## y
``` python
window.y
```
Get Y coordinate of the top-left corrner of the window

## width

``` python
window.width
```

Get width of the window

## height

``` python
window.height
```

Get height of the window

## create_file_dialog

``` python
window.create_file_dialog(dialog_type=OPEN_DIALOG, directory='', allow_multiple=False, save_filename='', file_types=())`
```

Create an open file (`webview.OPEN_DIALOG`), open folder (`webview.FOLDER_DIALOG`) or save file (`webview.SAVE_DIALOG`) dialog.

Return a tuple of selected files, None if cancelled.
  * `allow_multiple=True` enables multiple selection.
  * `directory` Initial directory.
  * `save_filename` Default filename for save file dialog.
  * `file_types` A tuple of supported file type strings in the open file dialog. A file type string must follow this format `"Description (*.ext1;*.ext2...)"`.

If the argument is not specified, then the `"All files (*.*)"` mask is used by default. The 'All files' string can be changed in the localization dictionary.

### Examples

* [Open-file dialog](/examples/open_file_dialog.html)
* [Save-file dialog](/examples/save_file_dialog.html)


## destroy

``` python
window.destroy()
```

Destroy the window.

[Example](/examples/destroy_window.html)

## evaluate_js

``` python
window.evaluate_js(script)
```

Execute Javascript code. The last evaluated expression is returned. Javascript types are converted to Python types, eg. JS objects to dicts, arrays to lists, undefined to None. Note that due implementation limitations the string 'null' will be evaluated to None.
You must escape \n and \r among other escape sequences if they present in Javascript code. Otherwise they get parsed by Python. r'strings' is a recommended way to load Javascript. For GTK WebKit2 versions older than 2.22, there is a limit of about ~900 characters for a value returned by `evaluate_js`.

## get_current_url

``` python
window.get_current_url()
```

Return the current URL. None if no url is loaded.

[Example](/examples/get_current_url.html)

## get_elements

``` python
window.get_elements(selector)
```

Return the serialized DOM element by its selector. None if no element matches. For GTK you must have WebKit2 2.22 or greater to use this function.

[Example](/examples/get_elements.html)

## hide

``` python
window.hide()
```

Hide the window.

[Example](/examples/show_hide.html)


## load_css

``` python
window.load_css(css)
```

Load CSS as a string.

[Example](/examples/css_load.html)


## load_html

``` python
window.load_html(content, base_uri=base_uri())
```

Load HTML code. Base URL for resolving relative URLs is set to the directory the program is launched from. Note that you cannot use hashbang anchors when HTML is loaded this way.

[Example](/examples/html_load.html)

## load_url

``` python
window.load_url(url)
```

Load a new URL.

[Example](/examples/change_url.html)

## minimize

``` python
window.minimize()
```

Minimize window.

[Example](/examples/minimize.html)

## move

``` python
window.move(x, y)
```

Move window to a new position.

[Example](/examples/move_window.html)


## restore

``` python
window.restore()
```

Restore minimized window.

[Example](/examples/minimize.html)


## set_title

``` python
window.set_title(title)
```

Change the title of the window.

[Example](/examples/window_title_change.html)

## show

``` python
window.show()
```

Show the window if it is hidden. Has no effect otherwise

[Example](/examples/show_hide.html)

## toggle_fullscreen

``` python
window.toggle_fullscreen()
```

Toggle fullscreen mode on the active monitor.

[Example](/examples/toggle_fullscreen.html)

# Events

Window object has a number of lifecycle events. To subscribe to an event, use the `+=` syntax, e.g. `window.events.loaded += func`. The func will be invoked, when event is fired. Duplicate subscriptions are ignored and function is invoked only once for duplicate subscribers. To unsubscribe `window.events.loaded -= func`.

## closed
Event fired just before pywebview window is closed.

[Example](/examples/events.html)

## closing
Event fired when pywebview window is about to be closed. If confirm_quit is set, then this event is fired before the close confirmation is displayed. If event handler returns False, the close operation will be cancelled.

[Example](/examples/events.html)

## loaded
Event fired when DOM is ready.

[Example](/examples/events.html)

## on_minimized
Event fired when window is minimzed.

[Example](/examples/events.html)

## on_restore
Event fired when window is restored.

[Example](/examples/events.html)

## on_maximized
Event fired when window is maximized (fullscreen on macOS)

## shown
Event fired when pywebview window is shown.

[Example](/examples/events.html)



# DOM events

_pywebview_ exposes a `window.pywebviewready` DOM event that is fired when `window.pywebview` is created.

[Example](/examples/js_api.html)


# Drag area

_pywebview_ window can be moved by dragging any element with the `pywebview-drag-region` class name. This is useful, for example, in frameless mode when you would like to implement a custom caption bar. The magic class name can be overriden by re-assigning the `webview.DRAG_REGION_SELECTOR` constant.


[Example](/examples/js_api.html)

