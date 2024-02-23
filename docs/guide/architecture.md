# Application architecture

There are two ways to build your application using _pywebview_:

1. By running a local web server. You can use the built-in server (based on bottle.py) or use your own.
2. Serverless with _pywebview_'s JS API  or `window.expose` and serving local files or load html directly.

## Local web server

Running a local web server is a traditional way to build your local application. This way everything is served from a local web server and _pywebview_ points to the URL provided by the server. In this model the server is responsible for both serving static contents and handling API calls. When using a local web server, you should protect your API calls against CSRF attacks. See [security](/guide/security.html) for more information.

See an example [Flask-based application](https://github.com/r0x0r/pywebview/tree/master/examples/flask_app)

## Serverless

Another way to build an application is to use _pywebview_'s provided JS API or `window.expose` and serve static files from a HTTP server. To serve static contents, set url to a local relative path. This will start a HTTP server automatically. For communication between Python and Javascript refer to [interdomain communication](/guide/interdomain.html).

See an example [serverless application](https://github.com/r0x0r/pywebview/tree/master/examples/todos)

You can also load HTML directly without a HTTP server using `webview.create_window(...html='')` or `window.load_html`. This approach has got limitations though, as file system does not exist in the context of the loaded page. Images and other assets can be loaded only inline using Base64.
