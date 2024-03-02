# Usage

## Basics

The bare minimum to get _pywebview_ up and running is

``` python
import webview

window = webview.create_window('Woah dude!', 'https://pywebview.flowrl.com')
webview.start()
```

The `create_window` function creates a new window and returns a `Window` object instance. Windows created before `webview.start()` are shown as soon as the GUI loop is started. Windows created after the GUI loop is started are shown immediately. You may create as many windows as you wish. All the opened windows are stored as a list in `webview.windows`. The windows are stored in a creation order.

``` python
import webview

first_window = webview.create_window('Woah dude!', 'https://pywebview.flowrl.com')
second_window = webview.create_window('Second window', 'https://woot.fi')
webview.start()
```

_pywebview_ gives a choice of using several web renderers. To change a web renderer, set the `gui` parameter of the `start` function to the desired value (e.g `cef` or `qt`). See [Renderer](/guide/renderer.md) for details.


## Backend logic

`webview.start` starts a GUI loop and blocks further code from execution until last window is destroyed. With the GUI loop being blocking, you must execute your backend logic in a separate thread or a process. You can execute your backend code by passing your function to `webview.start(func, (params,))`. This will launch a separate thread and is identical to starting a thread by hand.

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

## Communication between Javascript and Python

You can both run Javascript code from Python and vice versa. To run Javascript from Python, use `window.evaluate_js(code)`. The function returns result of the last line in the Javascript code. If code returns a promise, you can resolve it by passing a callback function `window.evaluate_js(code, callback)`. If Javascript throws an error, `window.evaluate_js` raises a `webview.errors.JavascriptException`.

To run Python from Javascript, you need to expose your API class with `webview.create_window(url, js_api=api_instance)`. Class member functions will be available in Javascript domain as `window.pywebview.api.funcName`. You may  expose single functions with `window.expose(func)` also during the runtime. See [interdomain communication](/guide/interdomain.md) for details.

``` python
import webview

class Api():
  def log(self, value):
    print(value)

webview.create_window("Test", html="<button onclick='pywebview.api.log(\"Woah dude!\")'>Click me</button>", js_api=Api())
webview.start()
```

Or alternatively you may use a more traditional approach with REST API paired with a WSGI server for interdomain communication. See [Flask app](https://github.com/r0x0r/pywebview/tree/master/examples/flask_app) for an example.

## HTTP server

_pywebview_ uses internally [bottle.py](https://bottlepy.org) HTTP server for serving static files. Relative local paths are served with a built-in HTTP server. The entrypoint directory serves as a HTTP server root with everything under the directory and its directories shared. You may want to enable SSL for the server by setting `webview.start(ssl=True)`.

``` python
import webview

webview.create_window('Woah dude!', html='src/index.html')
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

If your intent is to serve files without an HTTP server using the `file://` protocol, you can achieve this by either using an absolute file path or by prefixing the path with the `file://` protocol.

``` python
import webview

# this will be served as file:///home/pywebview/project/index.html
webview.create_window('Woah dude!', '/home/pywebview/project/index.html')
webview.start()
```

### Loading HTML

Alternatively, you can load HTML by setting the `html` parameter or with `window.load_html` function. A limitation of this approach is that but file system does not exist in the context of the loaded page. Images and other assets can be loaded only inline using Base64.

``` python
import webview

webview.create_window('Woah dude!', html='<h1>Woah dude!<h1>')
webview.start()
```
