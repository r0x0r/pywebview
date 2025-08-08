
# API

## webview.active_window

``` python
webview.active_window()
```

Get an instance of the currently active window

## webview.create_window

``` python
webview.create_window(title, url=None, html=None, js_api=None, width=800, height=600,
                      x=None, y=None, screen=None, resizable=True, fullscreen=False,
                      min_size=(200, 100), hidden=False, frameless=False,
                      easy_drag=True, shadow=False, focus=True, minimized=False, maximized=False,
                      on_top=False, confirm_close=False, background_color='#FFFFFF',
                      transparent=False, text_select=False, zoomable=False,
                      draggable=False, server=http.BottleServer, server_args={},
                      localization=None)
```

Create a new _pywebview_ window and returns its instance. Can be used to create multiple windows (except Android). Window is not shown until the GUI loop is started. If the function is invoked during the GUI loop, the window is displayed immediately.

* `title` - Window title
* `url` - URL to load. If the URL does not have a protocol prefix, it is resolved as a path relative to the application entry point. Alternatively a WSGI server object can be passed to start a local web server.
* `html` - HTML code to load. If both URL and HTML are specified, HTML takes precedence.
* `js_api` - Expose a python object to the Javascript domain of the current `pywebview` window. Methods of the `js_api` object can be invoked from Javascript by calling `window.pywebview.api.<methodname>(<parameters>)` functions. Exposed function return a promise that return once function returns. Only basic Python objects (like int, str, dict, ...) can be returned to Javascript.
* `width` - Window width. Default is 800px.
* `height` - Window height. Default is 600px.
* `x` - Window x coordinate. Default is centered.
* `y` - Window y coordinate. Default is centered.
* `screen` - Screen to display window on. `screen` is a screen instance returned by `webview.screens`.
* `resizable` - Whether window can be resized. Default is True
* `fullscreen` - Start in fullscreen mode. Default is False
* `min_size` - a (width, height) tuple that specifies a minimum window size. Default is 200x100
* `hidden` - Create a window hidden by default. Default is False
* `frameless` - Create a frameless window. Default is False.
* `easy_drag` - Easy drag mode for frameless windows. Window can be moved by dragging any point. Default is True. Note that easy_drag has no effect with normal windows. To control dragging on an element basis, see [drag area](/api.html#drag-area) for details.
* `shadow` - Add window shadow. Default is False. _Windows only_.
* `focus` - Create a non-focusable window if False. Default is True.
* `minimized` - Display window minimized
* `maximized` - Display window maximized
* `on_top` - Set window to be always on top of other windows. Default is False.
* `confirm_close` - Whether to display a window close confirmation dialog. Default is False
* `background_color` - Background color of the window displayed before WebView is loaded. Specified as a hex color. Default is white.
* `transparent` - Create a transparent window. Not supported on Windows. Default is False. Note that this setting does not hide or make window chrome transparent. To hide window chrome set `frameless` to True.
* `text_select` - Enables document text selection. Default is False. To control text selection on per element basis, use [user-select](https://developer.mozilla.org/en-US/docs/Web/CSS/user-select) CSS property.
* `zoomable` - Enable document zooming. Default is False
* `draggable` - Enable image and link object dragging. Default is False
server=http.BottleServer, server_args
* `vibrancy` - Enable window vibrancy. Default is False. macOS only.
* `server` - A custom WSGI server instance for this window. Defaults to BottleServer.
* `server_args` - Dictionary of arguments to pass through to the server instantiation
* `localization` - pass a localization dictionary for per window localization.

## webview.start

``` python
webview.start(func=None, args=None, localization={}, gui=None, debug=False,
              http_server=False, http_port=None, user_agent=None, private_mode=True,
              storage_path=None, menu=[], server=http.BottleServer, ssl=False,
              server_args={}, icon=None):
```

Start a GUI loop and display previously created windows. This function must be called from a main thread.

* `func` - function to invoke upon starting the GUI loop.
* `args` - function arguments. Can be either a single value or a tuple of values.
* `localization` - a dictionary with localized strings. Default strings and their keys are defined in localization.py
* `gui` - force a specific GUI. Allowed values are `cef`, `qt` or `gtk` depending on a platform. See [Web Engine](/guide/web_engine.md) for details.
* `debug` - enable debug mode. See [Debugging](/guide/debugging.md) for details.
* `http_server` - enable built-in HTTP server for absolute local paths. For relative paths HTTP server is started automatically and cannot be disabled. For each window, a separate HTTP server is spawned. This option is ignored for non-local URLs.
* `http_port` - specify a port number for the HTTP server. By default port is randomized.
* `user_agent` - change user agent string.
* `private_mode` - Control whether cookies and other persistant objects are stored between session. By default private mode is on and nothing is stored between sessions.
* `storage_path` - An optional location on hard drive where to store persistant objects like cookies and local storage. By default `~/.pywebview` is used on *nix systems and `%APPDATA%\pywebview` on Windows.
* `menu` - Pass a list of Menu objects to create an application menu. See [this example](/examples/menu.html) for usage details.
* `server` - A custom WSGI server instance. Defaults to BottleServer.
* `ssl` - If using the default BottleServer (and for now the GTK backend), will use SSL encryption between the webview and the internal server. You need to have `cryptography` pip dependency installed in order to use `ssl`. It is not installed by default.
* `server_args` - Dictionary of arguments to pass through to the server instantiation
* `icon` - path to application icon. Available only for GTK / QT. For other platforms icon should be specified via a bundler.

#### Examples

* [Simple window](/examples/open_url.html)
* [Multi-window](/examples/multiple_windows.html)

## webview.screens

``` python
webview.screens
```

Return a list of available displays (as `Screen` objects) with the primary display as the first element of the list.

#### Examples

* [Simple window](/examples/screens.html)

## webview.settings

``` python
webview.settings = {
  'ALLOW_DOWNLOADS': False,
  'ALLOW_FILE_URLS': True,
  'OPEN_EXTERNAL_LINKS_IN_BROWSER': True,
  'OPEN_DEVTOOLS_IN_DEBUG': True,
  'REMOTE_DEBUGGING_PORT': None,
  'SHOW_DEFAULT_MENUS': True
}
```

Additional options that override default behaviour of _pywebview_ to address popular feature requests.

* `ALLOW_DOWNLOADS` Allow file downloads. Disabled by default.
* `ALLOW_FILE_URLS` Enable `file://` urls. Disabled by default.
* `OPEN_EXTERNAL_LINKS_IN_BROWSER`. Open `target=_blank` link in an external browser. Enabled by default.
* `OPEN_DEVTOOLS_IN_DEBUG` Open devtools automatically in debug mode. Enabled by default.
* `REMOTE_DEBUGGING_PORT` Enable remote debugging when using `edgechromium`. Disabled by default.
* `SHOW_DEFAULT_MENUS` Show default application menus on macOS. Enabled by default.

#### Examples

* [File downloads](/examples/downloads.html)


## webview.token

``` python
webview.token
```

A CSRF token property unique to the session. The same token is exposed as `window.pywebview.token`. See [Security](/guide/security.md) for usage details.

## webview.dom

### webview.dom.DOMEventHandler

``` python
DOMEventHandler(callback, prevent_default=False, stop_propagation=False, stop_immediate_propagation=False, debounce=0)
```

A container for an event handler used to control propagation or default behaviour of the event. If `debounce` is greater than zero, Python event handler is debounced by a specified number of milliseconds. This can be useful for events like `dragover` and `mouseover` that generate a constant stream of events resulting in poor performance.

#### Examples

``` python
element.events.click += DOMEventHandler(on_click, prevent_default=True, stop_propagation=True, stop_immediate_propagation=True)
element.events.mouseover += DOMEventHandler(on_click, debounce=500)
```

### webview.dom.ManipulationMode

Enum that sets the position of a manipulated DOM element. Possible values are:

* `LastChild` - element is inserted as a last child of the target
* `FirstChild` - element is inserted as a firt child of the target
* `Before` - element is inserted before the target
* `After` - element is inserted after the target
* `Replace` - element is inserted replacing the target

Used by `element.append`, `element.copy`, `element.move` and `window.dom.create_element` functions.

## webview.Element

### element.attributes

Get or modify element's attributes. `attributes` is a `PropsDict` dict-like object that implements most of dict functions. To add an attribute, you can simply assign a value to a key in `attributes`. Similarly, to remove an attribute, you can set its value to None.

#### Examples

``` python
element.attributes['id'] = 'container-id' # set element's id
element.attributes['data-flag'] = '1337'
element.attributes['id'] = None # remove element's id
del element.attributes['data-flag'] # remove element's data-flag attribute
```

### element.classes

``` python
element.classes
```

Get or set element's classes. `classes` is a `ClassList` list-like object that implements a subset of list functions like `append`, `remove` and `clear`. Additionally it has a `toggle` function for toggling a class.

#### Examples

``` python
element.classes = ['container', 'red', 'dotted'] # overwrite element's classes
element.classes.remove('red') # remove red class
element.classes.add('blue') # add blue class
element.classes.toggle('dotted')
```

### element.append

``` python
element.append(html, mode=webview.dom.ManipulationMode.LastChild)
```

Insert HTML content to the element as a last child. To control the position of the new element, use the `mode` parameter. See [Manipulation mode](/api.html#manipulation-mode) for possible values.

### element.blur

``` python
element.blur()
```

Blur element.

### element.children

``` python
element.children
```

Get element's children elements. Returns a list of `Element` objects.

### element.copy

``` python
element.copy(target=None, mode=webview.dom.ManipulationMode.LastChild, id=None)
```

Create a new copy of the element. `target` can be either another `Element` or a DOM selector string. If target is omitted, a copy is created in the current element's parent. To control the position of the new element, use the `mode` parameter. See [Manipulation mode](/api.html#manipulation-mode) for possible values. The id parameter is stripped from the copy. Optionally you can set the id of the copy by specifying the `id` parameter.

### element.empty

``` python
element.empty()
```

Empty element by removing all its children.

### element.events

``` python
element.events
```

A container object of element's all DOM events, ie `events.click`, `event.keydown`. This container is dynamically populated and its contents depend on the events a node has. To subscribe to a DOM event, use the `+=` syntax, e.g. `element.events.click += callback`. Similarly to remove an event listener use `-=`, eg. `element.events.click -= callback`. Callback can be either a function or an instance of `DOMEventHandler` if you need to control propagation of the event.

### element.focus

``` python
element.focus()
```

Focus element.

### element.focused

``` python
element.focused
```

Get whether the element is focused.

### element.hide

``` python
element.hide()
```

Hide element by setting `display: none`.

### element.id

``` python
element.id
```

Get or set element's id. None if id is not set.

### element.move

``` python
element.move(target, mode=webview.dom.ManipulationMode.LastChild)
```

Move element to the `target` that can be either another `Element` or a DOM selector string.  To control the position of the new element, use the `mode` parameter. See [Manipulation mode](/api.html#manipulation-mode) for possible values.

#### Examples

[DOM Manipulation](/examples/dom_manipulation.html)

### element.next

``` python
element.next
```

Get element's next sibling. None if no sibling is present.

### element.off

``` python
element.off(event, callback)
```

Remove an event listener. Identical to `element.event.event_name -= callback`.

#### Examples

``` python
# these two are identical
element.off('click', callback_func)
element.events.click -= callback_func
```

[DOM Events](/examples/dom_events.html)

### element.on

``` python
element.on(event, callback)
```

Add an event listener to a DOM event. Callback can be either a function or an instance of `DOMEventHandler` if you need to control propagation of the event. Identical to `element.event.event_name += callback`.

#### Examples

```
# these two are identical
element.on('click', callback_func)
element.events.click += callback_func
```

[DOM Events](/examples/dom_events.html)

### element.parent

``` python
element.parent
```

Get element's parent `Element` or None if root element is reached.

### element.previous

``` python
element.previous
```

Get element's previous sibling. None if no sibling is present.

### element.remove

``` python
element.remove()
```

Remove element from DOM. `Element` object is not destroyed, but marked as removed. Trying to access any properties or invoke any functions of the element will result in a warning.

[DOM Manipulation](/examples/dom_manipulation.html)


### element.show

``` python
element.show()
```

Show hidden element. If element was hidden with `element.hide()`, a previous display value is restored. Otherwise `display: block` is set.

[DOM Manipulation](/examples/dom_manipulation.html)


### element.style

Get or modify element's styles. `style` is a `PropsDict` dict-like object that implements most of dict functions. To add a style declraration, you can simply assign a value to a key in `attributes`. Similarly, to reset a declaration, you can set its value to None.

#### Examples

``` python
element.style['width'] = '100px' # set element's width to 100px
element.style['display'] = 'flex' # set element's display property to flex
element.style['width'] = None # reset width to auto
del element.attributes['display'] # reset display property to block
```

### element.tabindex

``` python
element.tabindex
```

Get or set element's tabindex.

### element.tag

``` python
element.tag
```

Get element's tag name.

### element.text

``` python
element.text
```

Get or set element's text content.

### element.toggle

``` python
element.toggle()
```

Toggle element's visibility.

### element.value

``` python
element.value
```

Get or set element's value. Applicable only to input elements that have a value.

### element.visible

``` python
element.visible
```

Get whether the element is visible.

## webview.Menu

Used to create an application menu. See [this example](/examples/menu.html) for usage details.

### menu.Menu

`Menu(title, items=[])`.
Instantiate to create a menu that can be either top level menu or a nested menu. `title` is the title of the menu and `items` is a list of actions, separators or other menus.

### menu.MenuAction

`MenuAction(title, function)`
Instantiate to create a menu item. `title` is the name of the item and function is a callback that should be called when menu action is clicked.

### menu.MenuSeparator

`MenuSeparator()`
Instantiate to create a menu separator.

## webview.Screen

Represents a display found on the systems. A list of `Screen` objects is returned by `webview.screens` property.

### screen.height

``` python
screen.height
```

Get display height.

### screen.width

``` python
screen.width
```

### screen.x

``` python
screen.x
```

### screen.y

``` python
screen.y
```

Get display width.

## webview.Window

Represents a window that hosts webview. `window` object is returned by `create_window` function.

### window.title

``` python
window.title
```

Get or set title of the window.

### window.on_top

``` python
window.on_top
```

Get or set whether the window is always on top.

### window.x

``` python
window.x
```

Get X coordinate of the top-left corrner of the window.

### window.y

``` python
window.y
```

Get Y coordinate of the top-left corrner of the window.

### window.width

``` python
window.width
```

Get width of the window

### window.height

``` python
window.height
```

Get height of the window

### window.clear_cookies

``` python
window.clear_cookies()
```

Clear all the cookies including `HttpOnly` ones.

#### Example

* [Cookies](/examples/cookies.html)


### window.create\_confirmation\_dialog

``` python
window.create_confirmation_dialog(title, message)
```

Create a confirmation (Ok / Cancel) dialog.

### window.create\_file\_dialog

``` python
window.create_file_dialog(dialog_type=FileDialog.OPEN, directory='', allow_multiple=False, save_filename='', file_types=())
```

Create an open file (`webview.FileDialog.OPEN`), open folder (`webview.FileDialog.FOLDER`) or save file (`webview.FileDialog.SAVE`) dialog.

Return a tuple of selected files, None if cancelled.

  * `allow_multiple=True` enables multiple selection.
  * `directory` Initial directory.
  * `save_filename` Default filename for save file dialog.
  * `file_types` A tuple of supported file type strings in the open file dialog. A file type string must follow this format `"Description (*.ext1;*.ext2...)"`.

If the argument is not specified, then the `"All files (*.*)"` mask is used by default. The 'All files' string can be changed in the localization dictionary.

#### Examples

* [Open-file dialog](/examples/open_file_dialog.html)
* [Save-file dialog](/examples/save_file_dialog.html)

### window.destroy

``` python
window.destroy()
```

Destroy the window.

[Example](/examples/destroy_window.html)

### window.evaluate_js

``` python
window.evaluate_js(script, callback=None)
```

Execute Javascript code. The last evaluated expression is returned. If callback function is supplied, then promises are resolved and the callback function is called with the result as a parameter. Javascript types are converted to Python types, eg. JS objects to dicts, arrays to lists, undefined to None. DOM nodes are serialized using custom serialization. Functions are omitted and circular references are converted to the `[Circular Reference]` string literal. `webview.error.JavascriptException` is thrown if executed codes raises an error.
r-strings is a recommended way to load Javascript. Note that the `evaluate_js` employs `eval`, which will fail if `unsafe-eval` CSP is set. Alternatively you may use `window.run_js(code)` that executes Javascript code as is without returning a result.

### window.expose

Expose a Python function or functions to JS API. Functions are exposed as `window.pywebview.api.func_name`

[Example](/examples/expose.html)

### window.get_cookies

``` python
window.get_cookies()
```

Return a list of all the cookies set for the current website (as [SimpleCookie](https://docs.python.org/3/library/http.cookies.html)).

### window.get_current_url

``` python
window.get_current_url()
```

Return the current URL. None if no url is loaded.

[Example](/examples/get_current_url.html)

### window.get_elements

``` python
window.get_elements(selector)
```

*DEPRECATED*. Use `window.dom.get_elements` instead.

[Example](/examples/get_elements.html)

### window.hide

``` python
window.hide()
```

Hide the window.

[Example](/examples/show_hide.html)


### window.load_css

``` python
window.load_css(css)
```

Load CSS as a string.

[Example](/examples/css_load.html)


### window.load_html

``` python
window.load_html(content, base_uri=base_uri())
```

Load HTML code. Base URL for resolving relative URLs is set to the directory the program is launched from. Note that you cannot use hashbang anchors when HTML is loaded this way.

[Example](/examples/html_load.html)

### window.load_url

``` python
window.load_url(url)
```

Load a new URL.

[Example](/examples/change_url.html)

### window.maximize

``` python
window.maximize()
```

Maximize window.

[Example](/examples/window_state.html)

### window.minimize

``` python
window.minimize()
```

Minimize window.

[Example](/examples/window_state.html)

### window.move

``` python
window.move(x, y)
```

Move window to a new position.

[Example](/examples/move_window.html)


### window.native

``` python
window.native.Handle # get application window handle on Windows
```

Get a native window object. This can be useful for applying custom styling to the window. Object type depends on the platform

`System.Windows.Form` - Windows
`AppKit.NSWindow` - macOS
`Gtk.ApplicationWindow` - GTK
`QMainWindow` - QT
`kivy.uix.widget.Widget` - Android

The `native` property is available after the `before_show` event is fired.

You can also each platform's WebView object via `window.native.webview`. WebView's types are as follows.

`Microsoft.Web.WebView2.WinForms.WebView2` - Windows / EdgeChromium
`System.Windows.Forms.WebBrowser` - Windows / MSHTML
`WebKit.WKWebView` - macOS
`gi.repository.WebKit2.WebView` - GTK
`QtWebEngineWidgets.QWebEngineView` /  `QtWebKitWidgets.QWebView`- QT
`android.webkit.WebView` - Android


### window.resize

``` python
window.resize(width, height, fix_point=FixPoint.NORTH | FixPoint.WEST)
```

Resize window. Optional parameter fix_point specifies in respect to which point the window is resized. The parameter accepts values of the `webview.window.FixPoint` enum (`NORTH`, `SOUTH`, `EAST`, `WEST`)

[Example](/examples/minimize.html)

### window.restore

``` python
window.restore()
```

Restore minimized window.

[Example](/examples/minimize.html)

### window.run_js

``` python
window.run_js('document.body.style.color = "deepred"')
```

Execute Javascript as is without wrapping it in `eval` and helper code. This function does not return a result.

[Example](/examples/run_js.html)


### window.set_title

``` python
window.set_title(title)
```

*DEPRECATED*. Use `window.title` instead. Change the title of the window.

[Example](/examples/window_title_change.html)

### window.show

``` python
window.show()
```

Show the window if it is hidden. Has no effect otherwise

[Example](/examples/show_hide.html)

### window.toggle_fullscreen

``` python
window.toggle_fullscreen()
```

Toggle fullscreen mode on the active monitor.

[Example](/examples/toggle_fullscreen.html)

### window.dom.body

``` python
window.body
```

Get document's body as an `Element` object

### window.dom.create_element

``` python
window.create_element(html, parent=None, mode=webview.dom.ManipulationMode.LastChild)
```

Insert HTML content and returns the Element of the root object. `parent` can be either another `Element` or a DOM selector string. If parent is omited, created DOM is attached to document's body. To control the position of the new element, use the `mode` parameter. See [Manipulation mode](/api.html#manipulation-mode) for possible values.

### window.dom.document

``` python
window.document
```

Get `window.document` of the loaded page as an `Element` object

### window.dom.get_element

``` python
window.get_element(selector: str)
```

Get a first `Element` matching the selector. None if not found.

### window.dom.get_elements

``` python
window.get_elements(selector: str)
```

Get a list of `Element` objects matching the selector.

### window.dom.window

Get DOM document's window `window` as an `Element` object

## Window events

Window object exposes various lifecycle and window management events. To subscribe to an event, use the `+=` syntax, e.g., `window.events.loaded += func`. Duplicate subscriptions are ignored, and the function is invoked only once for duplicate subscribers. To unsubscribe, use the `-=` syntax, e.g., `window.events.loaded -= func`. To access the window object from the event handler, supply the `window` parameter as the first positional argument of the handler. Most window events are asynchronous, and event handlers are executed in separate threads. The `before_show` and `before_load` events are synchronous and block the main thread until handled.

### window.events.before_show

This event is fired just before pywebview window is shown. This is the earliest event that exposes `window.native` property. This event is blocking.

### window.events.before_load

The event is fired right before _pywebview_ code is injected into the page. The event roughly corresponds to `DOMContentLoaded` DOM event. This event is blocking.

### window.events.closed

The event is fired just before _pywebview_ window is closed.

[Example](/examples/events.html)

### window.events.closing

The event is fired when _pywebview_ window is about to be closed. If confirm_close is set, then this event is fired before the close confirmation is displayed. If event handler returns False, the close operation will be cancelled.

[Example](/examples/events.html)

### window.events.loaded

The event is fired when DOM is ready.

[Example](/examples/events.html)

### window.events.maximized

The event is fired when window is maximized (fullscreen on macOS)

### window.events.minimized

The event is fired when window is minimized.

[Example](/examples/events.html)

### window.events.moved

The event is fired when window is moved.

[Example](/examples/events.html)

### window.events.restored

The event is fired when window is restored.

[Example](/examples/events.html)

### window.events.resized

The event is fired when pywebview window is resized. Event handler can either have no or accept (width, height) arguments.

[Example](/examples/events.html)

### window.events.shown

The event is fired when pywebview window is shown.

[Example](/examples/events.html)

### window.state

An observable class object that holds the state shared between Python and Javascript. Setting any property of this state will result in `pywebview.state` having updated on the Javascript side and vice versa. State is unique to a window and is preserved between page loads. State changes fire events that can be subscribed as `pywebview.state += lambda event_type, key, value: pass`. `event_type` is either `change` or `delete` (`webview.state.StateEventType` enum). `key` is a property name and `value` for its value (`None` for delete events). See also [Javascript state events](#state-events)

## Javascript API

_pywebview_ create a global Javascript object `window.pywebview` that has following properties

### window.pywebview

A global Javascript object that exposes the following properties:

* `api` - A namespace for Python functions exposed via `window.expose` or `js_api` argument.
* `platform` - Current renderer in use.
* `token` - A CSRF token unique to the session that matches `webview.token` on the Python side.
* `state` - A shared state object between Python and Javascript.

## DOM events

### pywebviewready

_pywebview_ exposes a `window.pywebviewready` event that is fired after `window.pywebview` object is fully created.

[Example](/examples/js_api.html)

### State events

`pywebview.state` is an `EventTarget` object that fires two events `change` and `delete`. To subscribe to an event, use
`pywebview.state.addEventHandler('change', (e) => {})` or `pywebview.state.addEventHandler('delete', (e) => {})`. State change is stored in the `event.detail` object in form of `{ key, value }`

## Drag area

With a frameless _pywebview_ window, A window can be moved or dragged by adding a special class called `pywebview-drag-region` to any element.

```html
<div class='pywebview-drag-region'>Now window can be moved by dragging this DIV.</div>
```

The magic class name can be overriden by re-assigning the `webview.settings['DRAG_REGION_SELECTOR']` constant.

[Example](/examples/drag_region.html)
