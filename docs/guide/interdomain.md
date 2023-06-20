# Interdomain communication


## Invoke Javascript from Python

`window.evaluate_js(code, callback=None)` allows you to execute arbitrary Javascript code with a last value returned synchronously. If callback function is supplied, then promises are resolved and the callback function is called with the result as a parameter. Javascript types are converted to Python types, eg. JS objects to dicts, arrays to lists, undefined to None. Note that due implementation limitations the string 'null' will be evaluated to None.
You must escape \n and \r among other escape sequences if they present in Javascript code. Otherwise they get parsed by Python. r'strings' is a recommended way to load Javascript. For GTK WebKit2 versions older than 2.22, there is a limit of about ~900 characters for a value returned by `evaluate_js`.


## Invoke Python from Javascript
Invoking Python functions from Javascript can be done with two different approaches.

- by exposing an instance of a Python class to the `js_api` of `create_window`. All the callable methods  of the class will be exposed to the JS domain as `pywebview.api.method_name` with correct parameter signatures. Method name must not start with an underscore. See an [example](/examples/js_api.html).
- by passing your function(s) to window object's `expose(func)`. This will expose a function or functions to the JS domain as `pywebview.api.func_name`. Unlike JS API, `expose` allows to expose functions also at the runtime. If there is a name clash between JS API and functions exposed this way, the latter takes precedence. See an [example](/examples/expose.html).

Exposed function returns a promise that is resolved to its result value. Exceptions are rejected and encapsulated inside a Javascript `Error` object. Stacktrace is available via `error.stack`. Functions are executed in separate threads and are not thread-safe.

`window.pywebview.api` is not guaranteed to be available on `window.onload`. Subscribe to `window.pywebviewready` instead to make sure that `window.pywebview.api` is ready. [Example](/examples/js_api.html).
