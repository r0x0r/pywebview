# Usage


## Basics

The bare minimum to get _pywebview_ up and running is

``` python
import webview

window = webview.create_window('Woah dude!', 'https://pywebview.flowrl.com')
webview.start()
```

The `create_window` function returns a window instance that provides a number of both window manipulation and DOM related functions. You may create as many windows as you wish. Windows created after the GUI loop is started are shown immediately. All the opened windows are stored as a list in `webview.windows`. The windows are stored in a creation order.

The `create_window` second argument `url` can point to a remote or a local path. Alternatively, you can load HTML by setting the `html` parameter.

``` python
import webview

webview.create_window('Woah dude!', html='<h1>Woah dude!<h1>')
webview.start()
```

Note that if both `url` and `html` are set, `html` takes precedence.

_pywebview_ gives a choice of several web renderers. To change a web renderer, set the `gui` parameter of the `start` function to the desired value (e.g `cef` or `qt`). See [Renderer](/guide/renderer.md) for details.


## HTTP server

_pywebview_ provides a WSGI-compatible HTTP server. To start a HTTP server set the url to a local entry point (without a protocol schema) and set the `http_server` parameter of the `start` function to `True`

``` python
import webview

webview.create_window('Woah dude!', 'index.html')
webview.start(http_server=True)
```

If you wish to use an external WSGI compatible HTTP server with _pywebview_, you can pass a server object as an URL, ie. `http_server` parameter does not need to be set in this case.

``` python
from flask import Flask
import webview

server = Flask(__name__, static_folder='./assets', template_folder='./templates')
webview.create_window('Flask example', server)
webview.start()
```

## Threading model

`webview.start` starts a GUI loop and is a blocking function(for non-blocking see [Non-blocking mode](#non-blocking-mode)). With the GUI loop being blocking, you must execute your backend logic in a separate thread or a process. You may launch a thread or a process manually. Alternatively you can execute your code by passing your function as the first parameter `func` to `start`. The second parameter sets the function's arguments. This approach starts a thread behind the scenes and is identical to starting a thread manually.

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

## Non blocking mode

`webview.start(block=False)` starts a GUI loop and now it is a non-blocking function. Then you can do all other things normally. This is working like [Threading model](#threading-model) but main thread is free for other jobs and code is simple.(newly added by [@Ksengine](https://github.com/Ksengine))
``` python
import webview
import webview

# Master window
master_window = webview.create_window('Window #1', html='<h1>First window</h1>')
child_window = webview.create_window('Window #2', html='<h1>Second window</h1>')

process = webview.start(block = False)

# free main thread
# third window created after gui loop started
third_window = webview.create_window('Window #3', html='<h1>Third Window</h1>')

master_window.toggle_fullscreen()
master_window.evaluate_js('alert("Nice one brother")')

process.join()
# now blocked main thread. You can ommit above line to ever nonblocking main thread.
```


# Make Python and Javascript talk with each other

You can think of custom logic as a backend that communicates with frontend code in the HTML/JS realm. Now how would you make two to communicate with each other? _pywebview_ offers a two way JS-Python bridge that lets you both execute Javascript from Python (via `evaluate_js`) and Python code from Javascript (via `js_api` and `expose`). See [interdomain commmunication](/guide/interdomain.md) for details. Another way is to run a Python web server (like Flask or Bottle) in custom logic and make frontend code make API calls to it. That would be identical to a typical web application. This approach is suitable, for example, for porting an existing web application to a desktop application. See [Architecture](/guide/architecture.md) for more information on both approaches.





