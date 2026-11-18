---
prev: /guide/usage
---

# Application architecture

A _pywebview_ application has two parts:

- **Python code** that runs your application logic. It has full access to the system.
- **A web page** that shows the user interface. It runs in the system web engine.

When you design an application, you make two choices:

1. **How the page is loaded.** From a URL, from local files through an HTTP server, or as an HTML string.
2. **How the page talks to Python.** Through the built-in JS API bridge, or through HTTP requests to your own web server.

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
- Use `webview.start(ssl=True)` to serve the files over HTTPS.

Read more in [JS–Python bridge](/guide/interdomain.md) and [HTTP server](/guide/usage.md#http-server). See the [todos example](https://github.com/r0x0r/pywebview/tree/master/examples/todos) for a complete application.

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
