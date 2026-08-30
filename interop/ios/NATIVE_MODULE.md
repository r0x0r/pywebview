# `pywebview_ios` native-module contract

The embedded Python runtime must expose a module named `pywebview_ios`.
`webview.platforms.ios` uses the following functions:

| Function | Responsibility |
| --- | --- |
| `setup_app()` | Register the host/lifecycle callbacks. |
| `create_window(uid, title)` | Create or attach the single native WebView. |
| `destroy_window(uid)` | Tear down the WebView. |
| `load_url(url, uid)` | Navigate the WebView. |
| `load_html(html, base_uri, uid)` | Load inline content. |
| `evaluate_js(script, uid, parse_json)` | Evaluate JavaScript and return a Python value. |
| `get_current_url(uid)` | Return the current URL. |
| `get_cookies(uid)` / `clear_cookies(uid)` | Read and clear WebKit cookies. |
| `get_screens()` / `get_size(uid)` | Return mobile display information. |
| `set_title(title, uid)` | Update native title metadata where applicable. |
| `show(uid)` / `hide(uid)` | Show or hide the native host. |
| `toggle_fullscreen(uid)` | Toggle supported presentation state. |
| `create_confirmation_dialog(title, message, uid)` | Display a native confirmation dialog. |

Every function that touches UIKit or WebKit must marshal to the main thread.
Functions called from Python should either return a completed result or raise
a Python exception that the adapter can surface to the application.

The JavaScript bridge must post `{funcName, params, id}` messages to the
`jsBridge` handler. Python dispatch is handled by
`webview.util.js_bridge_call`; the native module must not duplicate API
reflection or callback semantics.
