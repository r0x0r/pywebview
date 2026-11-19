# Migrating to 7.0

_pywebview 7_ makes the JS API safe by default. In 6.x, every page shown in a window could call your Python API, read local files from `file://` pages and use some `Window` methods to widen its own access. In 7.0, only pages you trust get the API, and the bridge rejects calls that do not come from them.

Most applications that load their own local files need no changes. Read this guide if your application:

- loads remote sites, or navigates to other pages through links or redirects, and uses the JS API there
- loads pages from `file://` URLs
- stores a `Window` in its `js_api` object, or exposes `Window` methods
- opens non-web links in the system browser
- uses drag regions in windows with a native frame
- uses the MSHTML renderer or Python 3.9 or older

The complete list of changes is in the [changelog](/CHANGELOG.md). The [security guide](/guide/security.md) describes the security model in detail.

## Quick checklist

| If your application | Then |
| --- | --- |
| Uses the JS API on pages it navigates to | List their origins in `webview.settings['ALLOWED_ORIGINS']` |
| Loads a remote `http://` site with the JS API | Use HTTPS, or list the origin in `ALLOWED_ORIGINS` |
| Reads local files from a `file://` page | Serve the files through the built-in HTTP server, or set `webview.settings['ALLOW_FILE_URLS'] = True` |
| Loads `file://` pages on Qt | Serve the files through the built-in HTTP server, or set `webview.settings['ALLOW_FILE_URLS'] = True` |
| Calls `load_url`, `load_html`, `expose`, `evaluate_js`, `run_js` or `get_cookies` from Javascript | Wrap the call in a function of your own API |
| Stores a `Window` in a public attribute of `js_api` | Rename it to a private attribute, such as `self._window` |
| Sends bridge messages by hand | Call functions through `window.pywebview.api` |
| Opens custom URL schemes from links | Open them from Python |
| Uses `gui='mshtml'` | Install the WebView2 Runtime, or use `gui='cef'` |

## Which pages get the JS API

In 6.x, every page shown in a window got the JS API. In 7.0, a page gets it only when:

- you loaded it from Python, with `create_window`, `load_url` or `load_html`, or
- its origin is listed in `webview.settings['ALLOWED_ORIGINS']`.

An origin is a scheme, host and port, such as `https://example.com`. Pages from the built-in HTTP server and other loopback URLs, such as `http://127.0.0.1:5000` or `http://localhost:8000`, are loaded from Python and keep the JS API.

A page that the window reaches by following a link, a redirect or a `location.href` change does not get the API unless its origin is listed. For example, if your application loads `https://example.com` and the site redirects to `https://www.example.com`, list the second origin:

```python
import webview

webview.settings['ALLOWED_ORIGINS'] = ['https://www.example.com']

window = webview.create_window('App', 'https://example.com', js_api=Api())
webview.start()
```

### Plain HTTP from another machine

A plain `http://` URL on another machine does not get the JS API, even when you load it from Python, because anyone on the network path can change the page. _pywebview_ logs a warning for it. Use HTTPS, or list the origin in `ALLOWED_ORIGINS` if you accept the risk:

```python
webview.settings['ALLOWED_ORIGINS'] = ['http://192.168.1.10:8080']
```

### What a page without the JS API gets

A page without the JS API still gets `window.pywebview`, but:

- `window.pywebview.api` does not contain your functions,
- `window.pywebview.token` is an empty string,
- `window.state` is not synchronized with Python in either direction.

`evaluate_js()`, the DOM API and its event handlers, alert dialogs, drag regions and the `text_select`, `zoomable` and `draggable` window options keep working there.

If such a page opens while the window has a `js_api`, exposed functions or state values, _pywebview_ logs a warning with the page's URL. Look for this warning in the log when a page reports that an API function is not defined.

### When the decision is made

_pywebview_ decides whether a page gets the JS API when the page loads. If you change `ALLOWED_ORIGINS` while a page is open, the change takes effect from the next page load. Functions passed to `window.expose()` are not added to a page that does not have the JS API, and _pywebview_ logs a warning.

### Restoring the 6.x behaviour

Set `ALLOWED_ORIGINS` to `['*']` to give every page the JS API:

```python
webview.settings['ALLOWED_ORIGINS'] = ['*']
```

Use this only if the window can never show content you do not control. With `['*']`, any site the window reaches can call your Python API.

## Local files and `ALLOW_FILE_URLS`

`webview.settings['ALLOW_FILE_URLS']` is now `False` by default. Scripts on a `file://` page can no longer read other local files, for example with `fetch('file:///...')`. Android now uses this setting too.

On Qt, a `file://` page with the setting off cannot load its own scripts, styles and images either.

Pages served by the built-in HTTP server are not affected. If you pass a plain file path to `create_window`, such as `'index.html'`, _pywebview_ already serves it through the HTTP server, and you need no changes.

If you load `file://` URLs, the recommended fix is to pass a plain file path instead:

```python
# 6.x
window = webview.create_window('App', 'file:///home/user/app/index.html')

# 7.0
window = webview.create_window('App', 'app/index.html')
```

To keep the 6.x behaviour, enable the setting:

```python
webview.settings['ALLOW_FILE_URLS'] = True
```

### `load_url` and the served folder

`window.load_url()` raises `webview.SecurityException` for a local file outside the folder that the window's HTTP server serves. Keep all the files that a window loads in one folder, or create a separate window for files in another folder.

## Protected `Window` methods

The following `Window` methods can no longer be called from Javascript:

- `load_url`
- `load_html`
- `expose`
- `evaluate_js`
- `run_js`
- `get_cookies`

A page could use them to read local files, give the JS API to a site of its choice, run script in another document or read `HttpOnly` cookies. Python code, including your own API functions, can still call them.

If a `Window` is reachable through `js_api`, these methods are left out of `window.pywebview.api`, and _pywebview_ logs a warning for each of them:

```
window.load_url is protected and cannot be exposed to Javascript. Call it from a function of your own API instead, after checking its arguments.
```

`window.expose()` raises the new `webview.SecurityException` when you pass it one of these methods. `SecurityException` is a subclass of `WebViewException`, so existing `except WebViewException` blocks still catch it.

To keep calling one from Javascript, wrap it in a function of your own API and check its arguments there:

```python
# 6.x
class Api:
    def __init__(self):
        self.window = None

# Javascript: window.pywebview.api.window.load_url('settings.html')
```

```python
# 7.0
PAGES = {'home': 'index.html', 'settings': 'settings.html'}


class Api:
    def __init__(self):
        self._window = None

    def load_page(self, page):
        self._window.load_url(PAGES[page])

# Javascript: window.pywebview.api.load_page('settings')
```

### Keep the `Window` private

Store the `Window` in an attribute that starts with an underscore, such as `self._window`. Attributes that start with an underscore are not exposed to Javascript. A public attribute still exposes every `Window` method that is not protected, such as `destroy`, `create_file_dialog` and `clear_cookies`.

## Changes to the JS bridge

These changes affect only applications that use the bridge in unusual ways. Applications that call their API through `window.pywebview.api` need no changes.

- **Only advertised functions can be called.** The bridge dispatches calls only to the functions listed in `window.pywebview.api`. Hand-built bridge messages to other attribute paths of the `js_api` object are rejected and logged.
- **Calls are authorized per document.** Each document gets its own capability, which is revoked when the window navigates. `window.pywebview.token` no longer authorizes bridge calls. It is still the session token for protecting your own REST API against CSRF, as described in the [security guide](/guide/security.md#the-bridge-and-the-token).
- **Subframes do not get the API.** The JS API is injected only into the main document. Calls from `<iframe>` documents, or from documents without a source URL, are rejected. Call the API from the main document and pass the results to the frame with `postMessage`.
- **Deep `js_api` objects are cut off.** Nested `js_api` objects are walked to a depth of `webview.settings['JS_API_MAX_DEPTH']`, which is `10` by default. Raise it if your API is nested deeper.
- **The `/js_api` endpoint is removed.** The built-in HTTP server no longer has a `/js_api` endpoint, and the `Window.js_api_endpoint` and `BottleServer.js_api_endpoint` attributes are removed.

## External links

With `OPEN_EXTERNAL_LINKS_IN_BROWSER` enabled, which is the default, _pywebview_ opens only `http`, `https` and `mailto` links in the system browser. Links with other schemes, such as `file:` or an application-specific scheme, are logged and ignored. There is no setting to restore other schemes.

To open such a link, handle it in your API and open it from Python:

```python
import webbrowser


class Api:
    def open_in_app(self):
        webbrowser.open('myapp://settings')
```

## Window moves from the page

A page can move a window only if the window is frameless. This applies to drag regions and, on WebView2, to native drag requests. The new position is kept within the screens.

In 6.x, a drag region also moved a window with a native frame. In 7.0, it does nothing there. Use `frameless=True` if your window relies on a drag region to move:

```python
window = webview.create_window('App', 'index.html', frameless=True)
```

## Alerts

Page alerts are shown one at a time. Alerts that the page sends while one is open are dropped. On Qt, alerts are shown as plain text, so they no longer render links.

## SSL

`webview.start(ssl=True)` no longer turns off certificate checks for every site on EdgeChromium and Cocoa. Only the local HTTP server's own certificate is accepted, and other sites are validated as usual. If your application loads a remote site with an invalid certificate, set `webview.settings['IGNORE_SSL_ERRORS'] = True`. _pywebview_ logs a warning when a remote HTTPS page gets the JS API while this setting is enabled.

## Other breaking changes

These changes are not about security, but they can also break applications that upgrade from 6.x.

- **Python 3.10 or newer** is required.
- **The MSHTML renderer is removed.** `gui='mshtml'` is no longer accepted. On Windows, the WinForms backend requires the Edge WebView2 Runtime, or CEF with `gui='cef'`. Windows 7 and 8 without WebView2 are no longer supported.
- **`webview.screens` is a plain list.** It contains the screens at the time of access and is no longer re-queried on every use. It is also no longer exported by `from webview import *`; use `webview.screens`.
- **`http_port` in use raises `OSError`.** A port passed with `webview.start(http_port=...)` that is already in use raises `OSError` instead of failing silently.
- **`Window` properties raise `WebViewException`.** `window.width`, `height`, `x`, `y` and `title` raise `WebViewException` instead of `AttributeError` when the window is not ready.
- **State from Javascript is stored as values only.** Updates to `window.pywebview.state` from Javascript can no longer overwrite the internal attributes of `window.state` in Python.
