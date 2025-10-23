---
prev: /guide/usage
---

# Application architecture

There are several way to build your application using _pywebview_:

## Pure web server

- The most simple case is pointing to a url. This requires a running web server either remotely or locally

``` python
webview.create_window('Simple browser', 'https://pywebview.flowrl.com')
webview.start()
```

If you point to a local web server, you can start an external HTTP server in a background thread  manually and or giving a WSGIRef server instance to the url parameter.

``` python
server = Flask(__name__, static_folder='.', template_folder='.')
webview.create_window('My first pywebview application', server)
webview.start()
```

See a complete example [Flask-based application](https://github.com/r0x0r/pywebview/tree/master/examples/flask_app)

When using a local web server, you should protect your API calls against CSRF attacks. See [security](/guide/security.html) for more information.

While the `file://` protocol is possible, its use is discouraged as it comes with a number of inherit limitations and is not well supported.

## JS API with internal HTTP server

Another approach is using JS API bridge and serving static content with a built-in HTTP server.  JS API bridge allows communication between Python and Javascript domains without a web server. Thje bridge can be created either with `create_window(..., js_api=Api())` or `window.expose` function. To serve static contents, set entrypoint url to a local relative path. This will start a built-in HTTP server automatically. For more details on communication between Python and Javascript refer to [interdomain communication](/guide/interdomain.html). See an example [serverless application](https://github.com/r0x0r/pywebview/tree/master/examples/todos) for a complete implementation.

## Serverless

- Finally you can do without a web server altogther by loading HTML using `webview.create_window(...html='')` or `window.load_html`. This approach has got limitations though, as file system does not exist in the context of the loaded page. Images and other assets can be loaded only inline using Base64.
