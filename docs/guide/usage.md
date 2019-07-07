# Usage

The bare minimum to get _pywebview_ up and running is

``` python
import webview

window = webview.create_window('Woah dude!', 'https://pywebview.flowrl.com')
webview.start()
```

The `create_window` function returns a window instance that provides a number of functions. All the opened windows are stored as a list in `webview.windows`. The windows are stored in a creation order.

The `create_window` second argument `url` can point to a remote or a local path. Alternatively, you can load HTML by setting the `html` parameter.

``` python
import webview

webview.create_window('Woah dude!', html='<h1>Woah dude!<h1>')
webview.start()
```

Note that if both `url` and `html` are set, `html` takes precedence.

`webview.start` starts a GUI loop and itself is a blocking function. After starting the GUI loop, you must executed your logic in a separate thread. You can execute your code by passing your function as the first parameter `func` to `start`. The second parameter sets the function's arguments.

``` python
import webview

def custom_logic(window):
    window.evaluate_js('alert("Nice one brother")')

window = webview.create_window('Woah dude!', html='<h1>Woah dude!<h1>')
webview.start(custom_logic, window)
```

There are two ways to structure an application. Either by running a local web server and pointing _pywebview_ to it, or by employing JS API and `evaluate_js`. _pywebview_ also comes with a simple built-in web server that is good enough for serving local files. To use a local web server, set url to a local file and `webview.start(http_server=True)`.  See [Architecture](/guide/architecture.md) for more information.

To change a web renderer, set the `gui` parameter of the `start` function to the desired value (e.g `cef` or `qt`). See [Renderer](/guide/renderer.md) for details.

