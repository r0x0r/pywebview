# Javascript–Python bridge

_pywebview_ connects Javascript and Python without an HTTP server. There are three tools:

| Direction | Tool | Use it for |
| --- | --- | --- |
| Python → Javascript | `window.evaluate_js()`, `window.run_js()` | Running code in the page and reading results |
| Javascript → Python | `js_api` and `window.expose()` | Calling Python functions from the page |
| Both ways | `window.state` and `pywebview.state` | Data that both sides read and change |

Only pages that [get the JS API](/guide/security.md#which-pages-get-the-js-api) can call Python. Read the [Security](/guide/security.md) guide before you expose functions.

## Run Javascript from Python

`window.evaluate_js(code, callback=None)` runs Javascript in the page and returns the value of the last expression.

``` python
title = window.evaluate_js('document.title')
```

- Javascript values are converted to Python values: objects to `dict`, arrays to `list`, `undefined` and `null` to `None`.
- If the code throws an error, `evaluate_js` raises `webview.errors.JavascriptException` in Python.
- If the code returns a promise, pass a `callback`. _pywebview_ waits for the promise and calls the callback with the result.
- `evaluate_js` wraps your code in a helper and runs it with `eval`.

`window.run_js(code)` runs the code as it is, without a wrapper. It returns nothing and does not report errors. Use it when the page has a Content Security Policy that blocks `unsafe-eval`.

See the [evaluate_js example](/examples/evaluate_js.html).

## Run Python from Javascript

There are two ways to make Python functions available to Javascript. In both, a function becomes `pywebview.api.<name>` in the page.

### `js_api`

Pass an object to `create_window`. Its public methods are exposed. Names that start with an underscore are not exposed.

``` python
class Api:
    def add(self, a, b):
        return a + b

    def _private(self):  # not exposed
        pass

webview.create_window('API', 'index.html', js_api=Api())
```

- Methods and attributes with a name that starts with an underscore (`_name`) are never exposed. Use this for helpers and internal state.
- Nested objects are exposed as nested objects, for example `pywebview.api.files.read()`. Set `_serializable = False` on a class to hide it.
- Nesting is limited to `webview.settings['JS_API_MAX_DEPTH']` levels. The default is 10.

See the [js_api example](/examples/js_api.html).

### `expose`

`window.expose(func)` exposes one or more functions. Unlike `js_api`, you can call it at any time, including after the window has loaded. If an exposed function and a `js_api` method have the same name, the exposed function wins.

``` python
def hello(name):
    return f'Hello, {name}!'

window.expose(hello)
```

See the [expose example](/examples/expose.html).

### Calling from Javascript

Every call returns a promise.

``` javascript
window.addEventListener('pywebviewready', async () => {
  try {
    const result = await pywebview.api.add(1, 2)
  } catch (error) {
    console.error(error.stack)
  }
})
```

- The return value is serialized with Python's `json.dumps` and parsed in the page with `JSON.parse`. _pywebview_ does not use a custom encoder, so you can return only what `json.dumps` accepts: `dict`, `list`, `tuple`, `str`, `int`, `float`, `bool` and `None`.
  - Tuples become arrays, and dict keys become strings.
  - Other types raise a `TypeError`, and the promise is rejected with it. Examples are `bytes`, `set`, `datetime` and your own classes. Convert them first, for example a `datetime` with `.isoformat()` and `bytes` with Base64.
  - `NaN` and `Infinity` are not valid JSON. Do not return them.
- If the Python function raises an exception, the promise is rejected with a Javascript `Error`. The Python stack trace is in `error.stack`.
- Each call runs in its own thread. If your functions share data, protect it with locks.

### Wait for `pywebviewready`

`pywebview.api` is not guaranteed to exist when `window.onload` fires. Wait for the `pywebviewready` event.

``` javascript
window.addEventListener('pywebviewready', () => {
  // pywebview.api is ready
})
```

### Async functions

Exposed functions can be `async`. _pywebview_ runs coroutines on an asyncio event loop.

- If you pass a loop to `webview.start(event_loop=loop)`, _pywebview_ uses it. If the loop is not running, _pywebview_ runs it in a background thread.
- Otherwise, _pywebview_ starts its own loop in a background thread when the first coroutine runs, and closes it when the GUI loop exits.

These can also be `async`: handlers of non-blocking window events, DOM events and state changes, the function passed to `webview.start`, menu actions and `evaluate_js` callbacks. Handlers of blocking window events (`before_show`, `before_load`, `closing`, `initialized` and `request_sent`) must be regular functions. See [Window events](/api/#window-events) and the [async example](/examples/async_api.html).

Window methods such as `evaluate_js` are synchronous. If a coroutine calls one, the event loop waits until the call returns and no other coroutine can run. To avoid this, run the call in a thread:

``` python
await asyncio.to_thread(window.evaluate_js, script)
```

## Shared state

`NEW 6.0` `window.state` in Python and `pywebview.state` in Javascript are kept in sync. When one side sets a property, the other side gets the new value.

``` python
window.state.hello = 'world'  # pywebview.state.hello is now 'world'
```

- Only top-level properties are synchronized. If you change a nested object, assign it again to send the change.
- State belongs to one window and survives page reloads.
- Binary data is not supported. Encode it as Base64.

Both sides can listen for changes. The event type is `change` or `delete`. For `delete`, the value is `None`.

``` python
window.state += lambda event_type, key, value: print(event_type, key, value)
```

``` javascript
pywebview.state.addEventListener('change', event => console.log(event))
```

See the [state example](https://github.com/r0x0r/pywebview/blob/master/examples/state.py).
