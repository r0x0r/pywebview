# Application architecture

There are two ways to build your application using _pywebview_:

1. By running a local web server
2. Going serverless with _pywebview_'s JS API and serving local files.


## Local web server

Running a local web server is a traditional way to build your local application. This way everything is served from a local web server and _pywebview_ points to the URL provided by the server. In this model the server is responsible for both serving static contents and handling API calls.
When building an application this way, you should protect your API calls against CSRF attacks. See [security](/guide/security.html) for more information.

[Flask-based application](https://github.com/r0x0r/pywebview/tree/master/examples/flask_app)

**Pros**:
* Ability to pack an existing web application as a local one.
* Easier debugging with an external browser.

**Cons**
* Has to rely on a third party server software
* Security considerations must be taken into account


## Serverless
Another way to build an application is to use _pywebview_'s provided JS API and serve static files locally. When built this way, the application does not rely on any external libraries.

**Pros**:
* No external dependencies
* More straightforward architecture
* No risk of CSRF attacks

**Cons**
* Debugging has to be done inside the application using provided debugging tools

[Serverless application](https://github.com/r0x0r/pywebview/tree/master/examples/todos)
