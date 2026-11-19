---
prev: /guide/usage
---

# Application architecture

A _pywebview_ application has two parts:

- **Python code** that runs your application logic. It has full access to the system.
- **A web page** that shows the user interface. It runs in the system web engine.

When you design an application, you make two choices:

1. **How the page is loaded.** From a URL, from local files through an HTTP server, or as an HTML string.
2. **How the page and Python talk to each other.** Through the built-in JS API bridge and shared state, or through HTTP requests to your own web server. See [Communication between Python and the page](#communication-between-python-and-the-page).

The table below shows the common combinations.

| Approach | Content comes from | Page talks to Python with | Best for |
| --- | --- | --- | --- |
| [Built-in server + JS API](#built-in-server-and-js-api) | Local files, served by _pywebview_ | JS API | Most desktop applications |
| [Your own web framework](#your-own-web-framework) | A WSGI app such as Flask | HTTP requests (REST) | Existing web applications |
| [HTML string](#html-string) | A string in Python | JS API | Small tools and simple windows |
| [Remote URL](#remote-url) | A remote or local web server | HTTP requests | Wrapping an existing website |

You can mix these approaches. For example, a Flask application can also use the JS API for native features such as file dialogs.

In every approach, `webview.start()` blocks the main thread until the last window is closed. Run your own Python logic in a function passed to `webview.start(func)`, in event handlers or in a separate thread. See [Usage](/guide/usage.md#backend-logic).

## Built-in server and JS API

This is the recommended approach for most applications. Put your HTML, CSS and Javascript files in a directory and pass a relative path to `create_window`. _pywebview_ starts a built-in HTTP server and serves the directory of the entry file.

``` python
import webview

class Api:
    def greet(self, name):
        return f'Hello, {name}!'

webview.create_window('My application', 'assets/index.html', js_api=Api())
webview.start()
```

Javascript calls Python through `window.pywebview.api`. Each call returns a promise.

``` javascript
window.addEventListener('pywebviewready', async () => {
  const message = await window.pywebview.api.greet('world')
  console.log(message)
})
```

- Relative paths are resolved from the directory of your application entry point.
- Everything in the served directory and its subdirectories is available to the page. Do not put private files there.
- You can also expose single functions with `window.expose(func)`, at any time.
- Use `webview.start(ssl=True)` to serve the files over HTTPS (requires the `cryptography` library to be installed with `pip install cryptography`)

Read more in [HTTP server](/guide/usage.md#http-server). See the [todos example](https://github.com/r0x0r/pywebview/tree/master/examples/todos) for a complete application.

## Your own web framework

If you already have a web application, or prefer to use a web framework, pass a WSGI application object (for example, a Flask app) as the URL. _pywebview_ runs it on a local server and loads it in the window.

``` python
from flask import Flask
import webview

server = Flask(__name__, static_folder='./assets', template_folder='./templates')

@server.route('/')
def index():
    return 'Hello, world!'

if __name__ == '__main__':
    webview.create_window('Flask application', server)
    webview.start()
```

The page talks to Python with normal HTTP requests, such as `fetch()` calls to your REST API. You can also start your own server in a background thread and pass its `http://localhost:...` URL to `create_window`.

A local server can receive requests from other programs and web pages on the same computer. Protect your API against cross-site request forgery (CSRF) with `webview.token`. See [Security](/guide/security.md) for details and the [Flask example](https://github.com/r0x0r/pywebview/tree/master/examples/flask_app) for a complete application.

## HTML string

For small applications, you can skip files and servers. Pass HTML directly with `create_window(html=...)`, or load it later with `window.load_html()`. Use the JS API to talk to Python.

``` python
import webview

class Api:
    def log(self, value):
        print(value)

html = '<button onclick="pywebview.api.log(\'Clicked\')">Click me</button>'

webview.create_window('HTML string', html=html, js_api=Api())
webview.start()
```

This approach has limits. The page has no server behind it, and web engines handle access to local files differently. Images, styles and scripts may fail to load from relative paths. Put them inline, for example as Base64 `data:` URIs, or load them from a remote URL. If your application has many assets, use the [built-in server](#built-in-server-and-js-api) instead.

## Remote URL

The simplest application points the window to a URL. The page is served by a remote server or a server that you run yourself.

``` python
import webview

webview.create_window('Simple browser', 'https://pywebview.flowrl.com')
webview.start()
```

The page talks to its own server as in a normal browser. Be careful when you combine a remote URL with `js_api`: every page and script on that origin can then call your Python functions. Load only sites you control into such windows. See [Security](/guide/security.md#remote-pages).

## Local files with `file://`

You can load local files directly with an absolute path or a `file://` URL. This is not recommended. Web engines restrict `file://` pages in different ways, and absolute paths make the application harder to distribute. Use the [built-in server](#built-in-server-and-js-api) instead.

## Communication between Python and the page

Without your own web server, there are three ways for Python and the page to work together. You can use them together.

**JS API.** Javascript calls Python functions, as shown [above](#built-in-server-and-js-api). Use it for actions and for requests that return a result.

**Shared state.** `window.state` in Python and `window.pywebview.state` in Javascript are kept in sync. When one side sets a property, the other side gets the new value. Both sides can listen for changes. Use it for data that both sides read, such as settings or progress.

``` python
window.state.progress = 50  # Javascript now sees pywebview.state.progress === 50
```

Only top-level properties are synchronized. If you change a nested object, assign it again to send the change. See the [state example](https://github.com/r0x0r/pywebview/blob/master/examples/state.py).

**Driving the page from Python.** You can build and update the user interface from Python with little or no Javascript. `window.evaluate_js()` runs Javascript and returns the result. The DOM API (`window.dom`) creates, finds and changes elements, and lets you handle DOM events in Python.

``` python
button = window.dom.create_element('<button>Click me</button>')
button.events.click += lambda event: print('Clicked')
```

Read more in [JS–Python bridge](/guide/interdomain.md) and [DOM support](/guide/dom.md).

## Multiple windows

Each window loads its content independently, so windows in one application can use different approaches.

- Windows that load local files share one built-in HTTP server.
- A window that loads a WSGI application gets its own server.
- Use `create_window(http_port=...)` to choose the port of a window's server, and `server_args` to pass options to it.

See the [multiple servers example](https://github.com/r0x0r/pywebview/blob/master/examples/multiple_servers.py).

## Keeping data between runs

By default, _pywebview_ runs in private mode. Cookies, `localStorage` and other web storage are deleted when the application closes.

To keep them, use `webview.start(private_mode=False)`. Web storage belongs to an origin, which includes the port. For this reason, the built-in server then uses a fixed port (`webview.settings['DEFAULT_HTTP_PORT']`) instead of a random one. If that port is in use, it falls back to a random port, and stored data is not available in that run. To choose the port yourself, use `webview.start(http_port=...)`.

For important data, such as user files or settings, it is more reliable to save the data from Python, for example as a file in the user's application data directory.

## Packaging

Keep your web files in a directory next to your application and load them with a relative path. This works the same way after you package the application. Absolute paths break when the application is installed on another computer. See [Freezing](/guide/freezing.md).
