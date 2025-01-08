# Usage

## Basics

The bare minimum to get _pywebview_ up and running is

``` python
import webview

window = webview.create_window('Woah dude!', 'https://pywebview.flowrl.com')
webview.start()
```

The `create_window` function creates a new window and returns a `Window` object instance. Windows created before `webview.start()` are shown as soon as the GUI loop is started. Windows created after the GUI loop is started are shown immediately. You may create as many windows as you wish. All the opened windows are stored as a list in `webview.windows`. The windows are stored in a creation order. To get an instance of currently active (focused) window use `webview.active_window()`


``` python
import webview

def handler():
  print(f'There are {len(webview.windows)} windows')
  print(f'Active window: {webview.active_window().title}')

first_window = webview.create_window('pywebview docs', 'https://pywebview.flowrl.com')
second_window = webview.create_window('Woah dude!', 'https://woot.fi')
second_window.events.shown += handler
webview.start()
```

_pywebview_ gives a choice of using several web renderers. To change a web renderer, set the `gui` parameter of the `start` function to the desired value (e.g `cef` or `qt`). See [Web Engine](/guide/web_engine.md) for details.


## Backend logic

`webview.start` starts a GUI loop and blocks further code from execution until the last window is destroyed. Since the GUI loop is blocking, you must execute your backend logic in a separate thread or process. You can execute your backend code by passing your function to `webview.start(func, *args)`. This will launch a separate thread and is identical to starting a thread manually.

``` python
import webview

def custom_logic(window):
    window.toggle_fullscreen()
    window.evaluate_js('alert("Nice one brother")')

window = webview.create_window('Woah dude!', html='<h1>Woah dude!<h1>')
webview.start(custom_logic, window)
# anything below this line will be executed after program is finished executing
pass
```

## Window object

The `Window` object provides a number of functions and properties to interact with the window. Here are some of the commonly used methods.

- `window.load_url(url)`: Loads a new URL in the window.
- `window.load_html(content)`: Loads HTML content directly into the window.
- `window.evaluate_js(script)`: Executes JavaScript code in the window and returns the result.
- `window.toggle_fullscreen()`: Toggles the window between fullscreen and windowed mode.
- `window.resize(width, height)`: Resizes the window to the specified width and height.
- `window.move(x, y)`: Moves the window to the specified x and y coordinates.
- `window.hide()`: Hides the window.
- `window.show()`: Shows the window if it is hidden.
- `window.minimize()`: Minimizes the window.
- `window.restore()`: Restores the window if it is minimized or maximized.
- `window.destroy()`: Closes the window.

For a complete list of functions, refer to [API](/guide/api)

## Window events

Window object has these window manipulation and navigation events:  `closed`, `closing`, `loaded`, `before_load`, `before_show`, `shown`, `minimized`, `maximized`, `restored`, `resized`, `moved`. Window events can be found under the  `windod.events` container.

To subscribe to an event use the `+=` operator and `-=` for unsubscribing. For example:

``` python
import webview

def on_closing():
  print("Window is about to close")

window = webview.create_window('Woah dude!', 'https://pywebview.flowrl.com')
window.events.closing += on_closing
webview.start()
```

## Communication between Javascript and Python

You can both run Javascript code from Python and Python code from Javascript. To run Javascript from Python, use `window.evaluate_js(code)`. The function returns result of the last line in the Javascript code. If code returns a promise, you can resolve it by passing a callback function `window.evaluate_js(code, callback)`. If Javascript throws an error, `window.evaluate_js` raises a `webview.errors.JavascriptException`. Alternatively you may use `window.run_js(code)` that executes Javascript code as is. `run_js` does not return a result.

To run Python from Javascript, you need to expose your API class with `webview.create_window(url, js_api=api_instance)`. Class member functions will be available in Javascript domain as `window.pywebview.api.funcName`. You can expose single functions with `window.expose(func)` also during the runtime. See [interdomain communication](/guide/interdomain.md) for details.

``` python
import webview

class Api():
  def log(self, value):
    print(value)

webview.create_window("Test", html="<button onclick='pywebview.api.log(\"Woah dude!\")'>Click me</button>", js_api=Api())
webview.start()
```

Alternatively you may use a more traditional approach with REST API paired with a WSGI server for interdomain communication. See [Flask app](https://github.com/r0x0r/pywebview/tree/master/examples/flask_app) for an example.

## HTTP server

_pywebview_ uses internally [bottle.py](https://bottlepy.org) HTTP server for serving static files. HTTP server is launched automatically for relative local paths. The entrypoint directory serves as a HTTP server root with everything under the directory and its directories shared. You may want to enable SSL for the server by setting `webview.start(ssl=True)`.

``` python
import webview

webview.create_window('Woah dude!', 'src/index.html')
webview.start(ssl=True)
```

If you wish to use an external WSGI compatible HTTP server, you can pass a server application object as an URL.

``` python
from flask import Flask
import webview

server = Flask(__name__, static_folder='./assets', template_folder='./templates')
webview.create_window('Flask example', server)
webview.start()
```

If your intent is to serve files without an HTTP server using the `file://` protocol, you can achieve this by either using an absolute file path or by prefixing the path with the `file://` protocol. This approach is not recommended as it makes the program harder to distribute and has limitations on how it is handled by a web renderer.

``` python
import webview

# this will be served as file:///home/pywebview/project/index.html
webview.create_window('Woah dude!', '/home/pywebview/project/index.html')
webview.start()
```

### DOM support

_pywebview_ has got support for basic DOM manipulation, traversal operations and DOM events. See these examples for details [DOM Events](/examples/dom_events), [DOM Manipulation](/examples/dom_manipulation) and [DOM Traversal](/examples/dom_traversal).
