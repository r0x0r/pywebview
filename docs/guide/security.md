# Security

A _pywebview_ application has two halves. Your Python code runs with all the privileges of the user: it can read and write their files, run programs and use the network. The page runs in the system web engine, which keeps it away from all of that. The JS API is the bridge between the two, so every function you expose lets a page do something it could not do on its own.

This guide explains which pages can use that bridge, what they can reach through it, and what you need to take care of yourself.

## Security model

_pywebview_ treats Python as trusted and the page as untrusted. Even a page you wrote yourself can end up running code you did not write: a script from a CDN, an analytics snippet, or markup injected through a cross-site scripting bug. What a page can do is decided by three things:

1. **Which pages get the JS API.** Only pages you load from Python, and origins you list in `ALLOWED_ORIGINS`, can call your API. A page the window reaches on its own, by following a link or a redirect, cannot. See [Which pages get the JS API](#which-pages-get-the-js-api).
2. **What the API contains.** A page can call only the functions listed in `window.pywebview.api`. You decide what goes there, and _pywebview_ never exposes a few `Window` methods that would let a page widen its own access. See [What a page can call](#what-a-page-can-call).
3. **How calls are authenticated.** Every call over the bridge carries a capability that belongs to one document and is revoked when the window navigates. See [The bridge and the token](#the-bridge-and-the-token).

What _pywebview_ cannot protect you from:

- **A page with the JS API is as powerful as the API.** If an exposed function writes any file it is given, every script on a trusted page can write any file. Validate arguments as you would for a public web endpoint.
- **A trusted origin that is compromised.** Trust is given to a whole origin. If a site you load is compromised, or its domain changes hands, the attacker gets your API.
- **Data the page reports back.** Values returned by `evaluate_js()`, DOM events and `window.state` come from the page and can be forged by it.
- **Other programs on the same computer.** The built-in HTTP server listens on `127.0.0.1` without authentication, so any local program can read the files it serves. See [Local files](#local-files).

## Which pages get the JS API

A page gets the JS API in either of these cases:

- **You loaded it from Python.** This covers the URL passed to `create_window` or `load_url`, and HTML passed to `create_window(html=...)` or `load_html`. An HTTP(S) `base_uri` passed to `load_html` also grants its origin. The exception is plain `http://` from another machine, which anyone on the network path can modify: list such an origin in `ALLOWED_ORIGINS` if you need it, or better, use HTTPS. Loopback addresses such as `http://127.0.0.1` and `http://localhost`, which the built-in HTTP server uses, are granted as usual.
- **Its origin is listed in `webview.settings['ALLOWED_ORIGINS']`.** This is the only way for a page the window reaches on its own, by following a link, a redirect or a `location.href` change:

``` python
webview.settings['ALLOWED_ORIGINS'] = ['https://www.example.com']
```

`['*']` gives every page the API, as in older versions of _pywebview_. Avoid it in any window that can reach content you do not control.

How origins are matched:

- An origin is a scheme, host and port, such as `https://example.com` or `http://127.0.0.1:8080`. Every page on a granted origin gets the API, not just the page you loaded.
- Redirects count as navigation by the page. If `https://example.com` redirects to `https://www.example.com`, list the second origin.
- Non-HTTP documents are authorized by their exact URL, not by their entire scheme. Loading HTML does not authorize arbitrary `file:`, `data:` or `about:srcdoc` documents.
- Use the ASCII Punycode form for international hostnames with ambiguous Unicode mappings, such as `https://xn--fa-hia.example` for `https://faß.example`. Such Unicode spellings are rejected rather than authorizing a different hostname.

Whether a page gets the JS API is decided when it loads, and holds until the window navigates or reloads. Changing `ALLOWED_ORIGINS` while a page is open therefore takes effect from the next page load: a page that is already open keeps the access it was given. Functions passed to `window.expose()` while a page without the JS API is open are not added to it, and _pywebview_ logs a warning.

### Remote pages

Loading a remote URL into a window that has a JS API trusts that whole origin. Any page on it, and every script those pages include, such as analytics, advertising or a library from a CDN, can call your API. Load only sites you control into windows with a JS API, restrict what they load with a [Content Security Policy](#content-security-policy) and [subresource integrity](https://developer.mozilla.org/en-US/docs/Web/Security/Subresource_Integrity), and show third-party content, such as a login provider or documentation, in a separate window created without `js_api`.

`IGNORE_SSL_ERRORS` removes the protection HTTPS gives these pages, and _pywebview_ logs a warning when it is combined with a remote page that has the JS API.

### Pages without the JS API

A page that does not get the JS API still gets `window.pywebview`, but without your API: `window.pywebview.api` has none of your functions, `window.pywebview.token` is empty, and `window.state` is not synchronized with it in either direction. Calls it makes to your API are rejected. If the window has a `js_api`, exposed functions or values in `window.state`, _pywebview_ logs a warning naming the page's URL.

Everything else works there: `window.evaluate_js()`, the [DOM API](/guide/dom.md) including its event handlers, _pywebview_'s alert dialogs, drag regions and easy drag, and the `text_select`, `zoomable` and `draggable` options of `create_window`. This means any page can show a native alert, one at a time and as plain text, and drag a frameless window. Window moves from a page are ignored for windows that are not frameless.

## What a page can call

A page with the JS API can call the public methods of the `js_api` object, nested up to `JS_API_MAX_DEPTH` levels, and the functions passed to `window.expose()`. Nothing else: the bridge rejects any name not listed in `window.pywebview.api`. Attributes whose names start with an underscore are never exposed, and neither are objects marked with `_serializable = False`.

Treat every exposed function as a public endpoint:

- **Validate its arguments.** Do not pass page-supplied values unchecked to the file system, a shell, `eval` or SQL.
- **Expose only what the page needs.** Keep helpers and internal state in attributes starting with an underscore, or outside the `js_api` object altogether.
- **Keep the `Window` private.** Store it as `self._window`, never `self.window`. A public attribute exposes every method of the window that is not protected, such as `evaluate_js`, `create_file_dialog` and `destroy`.

### Protected methods

`window.load_url`, `window.load_html` and `window.expose` are protected: they are never exposed to Javascript, even when a `Window` is reachable through `js_api`. Called by a page, they could load `file://` URLs, or load a site of the page's choice, which would get the JS API as a page loaded from Python. _pywebview_ logs a warning when it leaves a protected method out of the API, and `window.expose()` raises `webview.SecurityException` if you pass it one.

Your own functions can still call them. To let a page navigate, check what it asks for and then call the protected method:

```python
PAGES = {'home': 'index.html', 'settings': 'settings.html'}


class Api:
    def __init__(self):
        self._window = None

    def load_page(self, page):
        self._window.load_url(PAGES[page])
```

## The bridge and the token

Calls over the native bridge are authorized by a capability that belongs to a single document. It is revoked when the window navigates (on document commit in Cocoa, so a failed provisional navigation does not disable the surviving page). The API is injected only into the main document, not into subframes.

`webview.token`, available in Javascript as `window.pywebview.token`, is a different thing. It is a session-unique value for protecting your own REST API against [CSRF attacks](https://owasp.org/www-community/attacks/csrf), that is, requests made by *other* sites. Every page that gets the JS API can read it, and knowing it does not grant bridge access. Send it with every request to your REST API and reject requests without it. See the [CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html) and the [Flask app example](https://github.com/r0x0r/pywebview/tree/master/examples/flask_app).

## Local files

When you pass a plain file path, such as `create_window('App', 'index.html')`, _pywebview_ serves the folder containing it through its built-in HTTP server on `127.0.0.1`. With several windows, it serves the folder that contains all their files. Files outside that folder are not served, and `load_url` raises `webview.SecurityException` for one. The server has no authentication, so any program on the computer can read what it serves: keep secrets out of that folder.

The server listens on the port passed to `webview.start(http_port=...)`. Without one, it uses a random port, or, with `private_mode=False`, the fixed port `DEFAULT_HTTP_PORT`, so that web storage persists between sessions. If that port is taken, it falls back to a random one and logs a warning.

`webview.start(ssl=True)` serves these files over HTTPS with a self-signed certificate. It needs the `cryptography` package, which you can install with `pip install "pywebview[ssl]"`.

`webview.settings['ALLOW_FILE_URLS']` lets scripts on a page loaded from a `file://` URL read any other local file the user can read, for example with `fetch('file:///...')`. It is `False` by default. Enable it only if your application needs it:

``` python
webview.settings['ALLOW_FILE_URLS'] = True
```

With the setting off, `file://` pages still load their own scripts, styles and images, except on Qt, where QtWebEngine blocks those as well. Serving your files through the built-in HTTP server avoids `file://` pages altogether.

## External links

With `OPEN_EXTERNAL_LINKS_IN_BROWSER` enabled (the default), links that open a new window, such as `target="_blank"` links, are handed to the system browser. Only `http`, `https` and `mailto` URLs are opened. Other schemes, such as `file:` or application-specific ones, are logged and ignored.

## Content Security Policy

A Content Security Policy limits where a page can load scripts and other resources from, so injected or third-party code cannot run. _pywebview_ evaluates scripts with `eval`, so the policy must allow `'unsafe-eval'`. Without it, `evaluate_js` and the JS API stop working. A reasonable starting point for content you ship yourself:

``` html
<meta http-equiv="Content-Security-Policy"
      content="default-src 'self'; script-src 'self' 'unsafe-eval'; object-src 'none'; base-uri 'none'">
```

`script-src 'self'` blocks inline `<script>` blocks and inline event handlers such as `onclick`, so move them into `.js` files.

## Checklist

- Load only content you control in windows that have a JS API, and keep `ALLOWED_ORIGINS` to the origins you need.
- Show third-party content in a separate window created without `js_api`.
- Validate the arguments of every exposed function, and expose only what the page needs.
- Keep the `Window` in a private attribute such as `self._window`.
- Leave `ALLOW_FILE_URLS` off, serve your files through the built-in HTTP server, and keep secrets out of the folder it serves.
- Use a Content Security Policy.
- Use `webview.token` to protect any REST API your page calls.
