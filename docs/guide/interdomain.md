# Javascript–Python bridge

_pywebview_ offers two-way communication between Javascript and Python, enabling interaction between the two languages without a HTTP server.

## Shared state

`NEW 6.0` Data can be shared via the `Window.state` (Python) and `pywebview.state` (Javascript) objects. Modifying any property on either state object will result in the state being updated on the other side and vice versa. For example, setting `window.state.hello = 'world'` in Python will automatically propagate to `pywebview.state.hello` in Javascript. State is specific to its window and is preserved between page (re)loads. Binary data can be passed by converting it to Base64 or such.

State changes trigger events that can be subscribed to using `pywebview.state += lambda event_type, key, value: pass`. The `event_type` is either `change` or `delete`. The `key` is the property name, and the `value` is the property's value (`None` for delete events).

## Run Javascript from Python

`window.evaluate_js(code, callback=None)` allows you to execute arbitrary Javascript code with a last value returned synchronously. If callback function is supplied, then promises are resolved and the callback function is called with the result as a parameter. Javascript types are converted to Python types, eg. JS objects to dicts, arrays to lists, undefined to None. If executed Javascript code results in an error, the error is rethrown as a `webview.util.JavascriptException` in Python. `evaluate_js` wraps Javascript code in a helper wrapper and executes it using `eval`.

[See example](/examples/evaluate_js.html)

`Window.run_js(code)` executes Javascript code as is without any wrapper code. `run_js` does not return a result or handle exceptions. This can be useful in scenarios, where you need to execute Javascript code with the `unsafe-eval` CSP policy set.

## Run Python from Javascript

Executing Python functions from Javascript can be done with two different mechanisms.

- by exposing an instance of a Python class to the `js_api` parameter of `create_window`. All the callable methods of the class will be exposed to the JS domain as `pywebview.api.method_name` with correct parameter signatures. Method name must not start with an underscore. Nested classes are allowed and are converted into a nested objects in Javascript. Class attributes starting with an underscore are not exposed. See an [example](/examples/js_api.html).

- by passing your function(s) to window object's `expose(func)`. This will expose a function or functions to the JS domain as `pywebview.api.func_name`. Unlike JS API, `expose` allows to expose functions also at the runtime. If there is a name clash between JS API and exposed functions, the latter takes precedence. See an [example](/examples/expose.html).

Exposed function returns a promise that is resolved to its result value. Exceptions are rejected and encapsulated inside a Javascript `Error` object. Stacktrace is available via `error.stack`. Exposed functions are executed in separate threads and are not thread-safe.

`pywebview.api` is not guaranteed to be available on the `window.onload` event. Subscribe to the `window.pywebviewready` event instead to make sure that `pywebview.api` is ready.

[See example](/examples/js_api.html).
