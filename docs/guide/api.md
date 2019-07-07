
# API

## webview.create_window

``` python
webview.create_window(title, url='', html='', js_api=None, width=800, height=600, resizable=True,\
                      fullscreen=False, min_size=(200, 100), confirm_close=False, \
                      background_color='#FFF', text_select=False)
```

Create a new _pywebview_ window and returns its instance. Window is not shown until the GUI loop is started. If the function is invoked during the GUI loop, the window is displayed immediately.

* `title` - Window title
* `url` - URL to load. If the URL does not have a protocol prefix, it is resolved as a path relative to the application entry point.
* `html` - HTML code to load. If both URL and HTML are specified, HTML takes precedence.
* `js_api` - Expose a `js_api` class object to the DOM of the current `pywebview` window. Callable functions of `js_api` can be executed using Javascript page via `window.pywebview.api` object. Custom functions accept a single parameter, either a primitive type or an object. Object types are converted between Javascript and Python. Functions are executed in separate
  threads and are not thread-safe. `window.pywebview` is not guaranteed to be available on `window.onload` and its access must be deferred.
* `width` - Window width. Default is 800px.
* `height` - Window height. Default is 600px.
* `resizable` - Whether window can be resized. Default is True
* `fullscreen` - Start in fullscreen mode. Default is False
* `frameless` - Create a frameless easy-draggable window. Default is False.
* `min_size` - a (width, height) tuple that specifies a minimum window size. Default is 200x100
* `confirm_close` - Whether to display a window close confirmation dialog. Default is False
* `background_color` - Background color of the window displayed before WebView is loaded. Specified as a hex color. Default is white.
* `text_select` - Enables document text selection. Default is False. To control text selection on per element basis, use [user-select](https://developer.mozilla.org/en-US/docs/Web/CSS/user-select) CSS property.

## webview.start

``` python
webview.start(func=None, args=None, localization={}, http_server=False, gui=None, debug=False)
```

Start a GUI loop and display previously created windows. This function must be called from a main thread.

* `func` - function to invoke upon starting the GUI loop.
* `args` - function arguments. Can be either a single value or a tuple of values.
* `localization` - a dictionary with localized strings. Default strings and their keys are defined in localization.py
* `http_server` - enable built-in HTTP server. If enabled, local files will be served using a local HTTP server on a random port. For each window, a separate HTTP server is spawned. This option is ignored for non-local URLs.
* `gui` - force a specific GUI. Allowed values are `cef`, `qt` or `gtk` depending on a platform. See [Renderer](/guide/renderer.md) for details.
* `debug` - enable debug mode. See [Debugging](/guide/debugging.md) for details.

### Examples
* [Simple window](/examples/open_url.html)
* [Multi-window](/examples/multiple_windows.html)

## webview.token

``` python
webview.token
```

A CSRF token property unique to the session. The same token is exposed as `window.pywebview.token`. See [Security](/guide/security.md) for usage details.


# Window object

These functions are part of the `window` object returned by `create_window`


## create_file_dialog

``` python
create_file_dialog(dialog_type=OPEN_DIALOG, directory='', allow_multiple=False, save_filename='', file_types=())`
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
destroy()
```

Destroy the window.

[Example](/examples/destroy_window.html)

## evaluate_js

``` python
evaluate_js(script)
```

Execute Javascript code. The last evaluated expression is returned. Javascript types are converted to Python types, eg. JS objects to dicts, arrays to lists, undefined to None. Note that due implementation limitations the string 'null' will be evaluated to None.
You must escape \n and \r among other escape sequences if they present in Javascript code. Otherwise they get parsed by Python. r'strings' is a recommended way to load Javascript. For GTK WebKit2 versions older than 2.22, there is a limit of about ~900 characters for a value returned by `evaluate_js`.

## get_current_url

``` python
get_current_url()
```

Return the current URL. None if no url is loaded.

[Example](/examples/get_current_url.html)

## get_elements

``` python
get_elements(selector)
```

Return the serialized DOM element by its selector. None if no element matches. For GTK you must have WebKit2 2.22 or greater to use this function.

[Example](/examples/get_element.html)

## load_css

``` python
load_css(css)
```

Load CSS as a string.

[Example](/examples/css_load.html)


## load_html

``` python
load_html(content, base_uri=base_uri())
```

Load HTML code. Base URL for resolving relative URLs is set to the directory the program is launched from. Note that you cannot use hashbang anchors when HTML is loaded this way.

[Example](/examples/html_load.html)

## load_url

``` python
load_url(url)
```

Load a new URL.

[Example](/examples/change_url.html)


## set_title

``` python
set_title(title)
```

Change the title of the window.

[Example](/examples/window_title_change.html)

## toggle_fullscreen

``` python
togle_fullscreen()
```

Toggle fullscreen mode on the active monitor.

[Example](/examples/toggle_fullscreen.html)

# Events

Window object has these lifecycle events. To subscribe to an event, use the `+=` syntax, e.g. `window.loaded += func`. The func will be invoked, when event is fired. Duplicate subscriptions are ignored and function is invoked only once for duplicate subscribers. To unsubscribe `window.loaded -= func`.

## shown
Event that is fired when pywebview window is shown.

[Example](/examples/events.html)


## loaded
Event that is fired when DOM is ready.

[Example](/examples/events.html)
