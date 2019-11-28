# Application architecture

There are two ways to build your application using _pywebview_:

1. By running a local web server
2. Serverless with _pywebview_'s JS API  or `window.expose` and serving local files.


## Local web server

Running a local web server is a traditional way to build your local application. This way everything is served from a local web server and _pywebview_ points to the URL provided by the server. In this model the server is responsible for both serving static contents and handling API calls. When building an application using a web server, you should protect your API calls against CSRF attacks. See [security](/guide/security.html) for more information.

See an example [Flask-based application](https://github.com/r0x0r/pywebview/tree/master/examples/flask_app)

**Pros**:
* Ability to pack an existing web application as a local one.
* Easier debugging with an external browser.

**Cons**
* Has to rely on a third party server software for client-server communication.
* Security considerations must be taken into account


## Serverless
Another way to build an application is to use _pywebview_'s provided JS API or `windows.expose` and serve static files locally.

_pywebview_ offers a simple built-in web server that is good enough for serving local files. To use a local web server, set url to a local file and start the application with `webview.start(http_server=True)`. Note that the built-in HTTP server serves only local files and does not offer any API calls. Refer to [interdomain communication](/guide/interdomain.html) for details on how to pass data between Python and Javascript.

See an example [serverless application](https://github.com/r0x0r/pywebview/tree/master/examples/todos)

**Pros**:
* No external dependencies
* More straightforward architecture
* No risk of CSRF attacks

**Cons**
* Debugging has to be done inside the application using provided debugging tools
* EdgeHTML cannot serve local files.

