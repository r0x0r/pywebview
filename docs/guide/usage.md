# Usage

## Basics

The bare minimum to get _pywebview_ up and running is

``` python
import webview

window = webview.create_window('Woah dude!', 'https://pywebview.flowrl.com')
webview.start()
```

The `create_window` function returns a `Window` object instance. You may create as many windows as you wish. Windows created after the GUI loop is started are shown immediately. All the opened windows are stored as a list in `webview.windows`. The windows are stored in a creation order.

The `create_window` second argument `url` can point to a remote or a local path. Alternatively, you can load HTML by setting the `html` parameter.

``` python
import webview

webview.create_window('Woah dude!', html='<h1>Woah dude!<h1>')
webview.start()
```

Note that if both `url` and `html` are set, `html` takes precedence.

_pywebview_ gives a choice of several web renderers. To change a web renderer, set the `gui` parameter of the `start` function to the desired value (e.g `cef` or `qt`). See [Renderer](/guide/renderer.md) for details.

## HTTP server

_pywebview_ includes a built-in WSGI-compatible HTTP server that relies on the bottle.py framework. To initiate the HTTP server, specify the URL as a local relative path to the HTML file, which will serve as the entry point. For local relative URLs, the HTTP server will start automatically.

``` python
import webview

# this will start the built-in HTTP server
webview.create_window('Woah dude!', 'index.html')
webview.start()
```

Enabling SSL for your local HTTP server is a wise step to safeguard local traffic from potential eavesdropping. To accomplish this, simply start the application with the `ssl` paramater set to True `webview.start(ssl=True)`.

If you wish to use an external WSGI compatible HTTP server with _pywebview_, you can pass a server object as an URL, ie. `http_server` parameter does not need to be set in this case.

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

## Threading model

`webview.start` starts a GUI loop and blocks further code from execution until last window is destroyed. With the GUI loop being blocking, you must execute your backend logic in a separate thread or a process. You can execute your backend code by passing your function as the first parameter `func` to the `start` function. The second parameter sets the function's arguments. This approach launches a thread behind the scenes and is identical to starting a thread manually.

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

Not all the code plays nice with multithreading, so you might want to execute background code in a separate process. You can do it like this.

``` python
import webview
from multiprocessing import Process

def custom_logic(window):
    window.toggle_fullscreen()
    window.evaluate_js('alert("Nice one brother")')

window = webview.create_window('Woah dude!', html='<h1>Woah dude!<h1>')
p = Process(target=custom_logic, args=(window,))
p.start()
webview.start()
# anything below this line will be executed after application is finished executing
pass
```

## Communication between Javascript and Python

Traditionally frontend and backend talk with each other by making requests to REST API provided by HTTP server. While this is a certainly an option, _pywebview_ also provides two-way communication between Javascript and Python domains. To execute Javascript code from Python you may use `window.evaluate_js` or skip Javascript altogether by using built-in [DOM functions](/guide/dom.html). To invoke Python functions from Javascript you can expose Python functions to Javascript via `js_api` and `window.expose`. Exposed functions are visible in Javascript as `window.pywebview.api.funcName`. See [interdomain communication](/guide/interdomain.md) for details.
