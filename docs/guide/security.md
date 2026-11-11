# Security

It is advisable to enable SSL for local HTTP server. To accomplish this, simply start the application with the `ssl` paramater set to True `webview.start(ssl=True)`. You need to have `cryptography` pip dependency installed in order to use `ssl`. It is not installed by default.

If you employ a REST API, [CSRF attacks](https://www.owasp.org/index.php/Cross-Site_Request_Forgery_(CSRF)) can be a major concern. _pywebview_ mitigates this risk by generating a session-unique token that is accessible in Python as `webview.token` and in JavaScript as `window.pywebview.token`. For more information on securing APIs, refer to the [CSRF Prevention Cheat Sheet](https://www.owasp.org/index.php/Cross-Site_Request_Forgery_\(CSRF\)_Prevention_Cheat_Sheet). You can also see a practical example in the [Flask app](https://github.com/r0x0r/pywebview/tree/master/examples/flask_app).

## The JS API and the page

Every script running in a window's page can call that window's JS API. That covers the public methods of the `js_api` object (nested up to `JS_API_MAX_DEPTH` levels) and the functions passed to `window.expose()`. Only the functions listed in `window.pywebview.api` can be called. Attributes whose names start with an underscore are never exposed.

`window.pywebview.token` does not decide which pages may use the JS API: every page that gets the API can read it. The token protects your own REST API from requests made by *other* sites (see above).

The native bridge uses a separate, per-document capability that is revoked on navigation (on document commit in Cocoa, so a failed provisional navigation does not disable the surviving page). Knowing the session's REST token does not grant bridge access. The API is injected only into the main document, not into subframes.

## Which pages get the JS API

Pages you load from Python get the JS API: the URL passed to `create_window` or `load_url`, and HTML passed to `create_window(html=...)` or `load_html`. The exception is plain `http://` from another machine, which anyone on the network path can modify: list such an origin in `ALLOWED_ORIGINS` if you need it, or better, use HTTPS. Loopback addresses such as `http://127.0.0.1` and `http://localhost`, which the built-in HTTP server uses, are granted as usual. A page the window reaches on its own, by following a link, a redirect or a `location.href` change, gets it only if its origin is listed in `webview.settings['ALLOWED_ORIGINS']`:

``` python
webview.settings['ALLOWED_ORIGINS'] = ['https://www.example.com']
```

An origin is a scheme, host and port, such as `https://example.com` or `http://127.0.0.1:8080`. A page from any other origin still gets `window.pywebview`, but without your API: `window.pywebview.api` has none of your functions, `window.pywebview.token` is empty, and, if the window has a `js_api`, exposed functions or values in `window.state`, _pywebview_ logs a warning naming the page's URL. Calls it makes to your API are rejected, and `window.state` is not synchronized with it in either direction. Everything else works there: `window.evaluate_js()`, the [DOM API](/guide/dom.md) including its event handlers, _pywebview_'s alert dialogs, drag regions and easy drag, and the `text_select`, `zoomable` and `draggable` options of `create_window`. Keep in mind that the page itself controls what `evaluate_js()` and DOM events report to Python. Because of that, any page can show a native alert, one at a time and as plain text, and drag a frameless window. Window moves from a page are ignored for windows that are not frameless. `['*']` restores the old behaviour of giving every page the API.

Use the ASCII Punycode form for international hostnames with ambiguous Unicode mappings, such as `https://xn--fa-hia.example` for `https://faß.example`. Such Unicode spellings are rejected rather than authorizing a different hostname.

Redirects count as navigation by the page. If `https://example.com` redirects to `https://www.example.com`, list the second origin.

Non-HTTP documents are authorized by their exact URL, not by their entire scheme. Loading HTML does not authorize arbitrary `file:`, `data:` or `about:srcdoc` documents. An HTTP(S) `base_uri` passed to `load_html` also authorizes that origin, under the same rule for plain HTTP.

Loading a remote URL into a window that has a JS API trusts that whole origin, not just the page. Any page on it, and every script those pages include, such as analytics, advertising or a library from a CDN, can call your API. If the site is compromised, or its domain changes hands, so is your application. Load only sites you control into windows with a JS API, restrict what they load with a Content Security Policy and [subresource integrity](https://developer.mozilla.org/en-US/docs/Web/Security/Subresource_Integrity), and show third-party content, such as a login provider or documentation, in a window without `js_api`. `IGNORE_SSL_ERRORS` removes the protection HTTPS gives these pages, and _pywebview_ logs a warning when it is combined with a remote page that has the JS API.

Treat every exposed function as a public endpoint:

- Validate its arguments. Do not pass page-supplied values unchecked to the file system, a shell, `eval` or SQL.
- Expose only what the page needs. Keep helpers and internal state in attributes starting with an underscore, or outside the `js_api` object altogether.
- Show untrusted or remote content in a separate window created without `js_api`.

## Local files

`webview.settings['ALLOW_FILE_URLS']` lets scripts on a page loaded from a `file://` URL read any other local file the user can read, for example with `fetch('file:///...')`. It is `False` by default. Enable it only if your application needs it:

``` python
webview.settings['ALLOW_FILE_URLS'] = True
```

With the setting off, `file://` pages still load their own scripts, styles and images, except on Qt, where QtWebEngine blocks those as well. Serving your files through the built-in HTTP server avoids `file://` pages altogether. This is what happens when you pass a plain file path, such as `create_window('App', 'index.html')`, rather than a `file://` URL.

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
- Validate the arguments of every exposed function.
- Leave `ALLOW_FILE_URLS` off, and serve your files through the built-in HTTP server.
- Use a Content Security Policy.
- Use `webview.token` to protect any REST API your page calls.
