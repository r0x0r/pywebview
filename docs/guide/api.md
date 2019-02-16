
# API

## create_window

``` python
create_window(title, url='', js_api=None, width=800, height=600, resizable=True,\
              fullscreen=False, min_size=(200, 100), strings={}, confirm_quit=False, \
              background_color='#FFF', debug=False, text_select=False)
```

Create a new _pywebview_ window. Calling this function for the first time will start the application and block program execution. You have to execute your program logic in a separate thread. Subsequent calls to `create_window` will return a unique window `uid`, which can be used to refer to the specific window in the API functions. Single-window applications need not bother about the `uid` and can simply omit it from function calls.

* `title` - Window title
* `url` - URL to load. If the URL does not have a protocol prefix, it is resolved as a path relative to the application entry point.
* `js_api` - Expose a `js_api` class object to the DOM of the current `pywebview` window. Callable functions of `js_api` can be executed using Javascript page via `window.pywebview.api` object. Custom functions accept a single parameter, either a
 primitive type or an object. Object types are converted between Javascript and Python. Functions are executed in separate
  threads and are not thread-safe.
* `width` - Window width. Default is 800px.
* `height` - Window height. Default is 600px.
* `resizable` - Whether window can be resized. Default is True
* `fullscreen` - Start in fullscreen mode. Default is False
* `frameless` - Create a frameless easy-draggable window. Default is False.
* `min_size` - a (width, height) tuple that specifies a minimum window size. Default is 200x100
* `strings` - a dictionary with localized strings. Default strings and their keys are defined in localization.py
* `confirm_quit` - Whether to display a quit confirmation dialog. Default is False
* `background_color` - Background color of the window displayed before WebView is loaded. Specified as a hex color. Default is white.
* `debug` - Enabled debug mode. See [debugging](/guide/debugging.html) for details
* `text_select` - Enables document text selection. Default is False. To control text selection on per element basis, use [user-select](https://developer.mozilla.org/en-US/docs/Web/CSS/user-select) CSS property.

The functions below must be invoked after a _pywebview_ window is created, otherwise an exception is thrown.
In all cases, `uid` is the uid of the target window returned by `create_window()`; if no window exists with the given `uid`, an exception is thrown. Default is `'master'`, which is the special uid given to the first window.


### Examples
* [Simple window](/examples/open_url.html)
* [Multi-window](/examples/multiple_windows.html)

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


## destroy_window

``` python
destroy_window(uid='master')
```

Destroy the specified WebView window.

[Example](/examples/destroy_window.html)

## evaluate_js

``` python
evaluate_js(script, uid='master')
```

Execute Javascript code in the specified window. The last evaluated expression is returned. Javascript types are converted to Python types, eg. JS objects to dicts, arrays to lists, undefined to None. Note that due implementation limitations the string 'null' will be evaluated to None.
You must escape \n and \r among other escape sequences if they present in Javascript code. Otherwise they get parsed by Python. r'strings' is a recommended way to load Javascript.

## get_current_url

``` python
get_current_url(uid='master')
```

Return the current URL in the specified window. None if no url is loaded.

[Example](/examples/get_current_url.html)

## load_css

``` python
load_css(css, uid='master')
```

Load CSS as string into the specified window.

[Example](/examples/css_load.html)



## load_html

``` python
load_html(content, base_uri=base_uri(), uid='master')
```

Load HTML code into the specified window. Base URL for resolving relative URLs is set to the directory the program is launched from. Note that you cannot use hashbang anchors when HTML is loaded this way.

[Example](/examples/html_load.html)

## load_url

``` python
load_url(url, uid='master')
```

Load a new URL into the specified _pywebview_ window.

[Example](/examples/change_url.html)


## set_title

``` python
set_title(title, uid='master')
```

Change the title of the window

[Example](/examples/window_title_change.html)

## toggle_fullscreen

``` python
togle_fullscree(uid='master')
```

Toggle fullscreen mode of a window on the active monitor.

[Example](/examples/toggle_fullscreen.html)

## window_exists

``` python
window_exists(uid='master')
```

Return True if a _pywebview_ window with the given uid is up and running, False otherwise.


## config

```
config.gui = 'qt' | 'gtk'
```

Force GUI library to either GTK or QT. The same setting can be controlled via `PYWEBVIEW_GUI` environmental variable






