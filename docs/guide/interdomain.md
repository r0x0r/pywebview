# Interdomain communication


## Invoke Javascript from Python

`window.evaluate_js(code)` allows you to execute arbitrary Javascript code. The result is returned synchronously. `null`, `NaN` and `undefined` are translated to `None`.


## Invoke Python from Javascript
Invoking Python functions from Javascript can be done with two different approaches.

- by exposing an instance of a Python class to the `js_api` of `create_window`. All the callable methods  of the class will be exposed to the JS domain as `pywebview.api.method_name` with correct parameter signatures. Method name must not start with an underscore. See an [example](/examples/js_api.html).
- by passing your function(s) to window object's `expose(func)`. This will expose a function or functions to the JS domain as `pywebview.api.func_name`. Unlike JS API, `expose` allows to expose functions also at the runtime. If there is a name clash between JS API and functions exposed this way, the latter takes precedence. See an [example](/examples/expose.html).

Exposed function returns a promise that is resolved to its result value. Exceptions are rejected and encapsulated inside a Javascript `Error` object. Stacktrace is available via `error.stack`. Functions are executed in separate threads and are not thread-safe.

`window.pywebview.api` is not guaranteed to be available on `window.onload`. Subscribe to `window.pywebviewready` instead to make sure that `window.pywebview.api` is ready. [Example](/examples/js_api.html).