---
next: /guide/installation
---

# Introduction

_pywebview_ is a lightweight library for building desktop applications with web technologies. It opens a native window that shows HTML, CSS and Javascript, and connects the page to your Python code.

_pywebview_ does not bundle a browser or a GUI toolkit. It uses the web engine that the operating system already provides. This keeps frozen applications small.

| Platform | Window | Web engine |
| --- | --- | --- |
| Windows | WinForms or WinUI 3 | WebView2 (Chromium). CEF is optional |
| macOS | Cocoa | WKWebView |
| Linux | GTK or Qt | WebKit2 or QtWebEngine |
| Android | Android | Android WebView |

See [Web engine](/guide/web_engine.md) for details.

## Features

- Window management: size, position, minimize, maximize, fullscreen, always on top, hide and show
- Multiple windows and multiple screens
- Frameless and transparent windows, custom title bars and drag areas
- Two-way communication between Javascript and Python: call Python functions from the page and run Javascript from Python
- Async support: exposed functions, event handlers and callbacks can be `async` functions that run on an asyncio event loop
- Shared state between Python and the page, synced in both directions
- DOM access from Python: find, create, change and move elements, and handle DOM events
- Events for the window lifecycle, such as `loaded`, `shown`, `resized` and `closing`
- Built-in HTTP server for local files. You can also serve a WSGI app, such as Flask, directly in a window. HTTPS is optional
- Native menus, file dialogs and confirmation dialogs
- Drag and drop of files with full file paths
- Cookies, private mode and persistent storage
- Downloads, custom user agent and localization of built-in strings

## When to use _pywebview_

_pywebview_ is a good fit when you want a desktop interface made with web technologies, and a small application that is easy to ship. It works with any frontend framework, such as React, Vue or plain HTML.

Because _pywebview_ uses the system web engine, your page runs in different engines on different platforms. Test your application on each platform you support. If you need exactly the same engine everywhere, a toolkit that bundles its own browser is a better choice.

## Install

``` bash
pip install pywebview
```

On some Linux systems you need to install extra libraries. See [Installation](/guide/installation.md).

## Hello world

``` python
import webview

webview.create_window('Hello world', 'https://pywebview.flowrl.com/')
webview.start()
```

`create_window` creates a window. `start` runs the GUI loop and blocks until the last window is closed.

To call Python from the page, expose a class with `js_api`.

``` python
import webview

class Api:
    def hello(self, name):
        return f'Hello, {name}!'

html = """
<button onclick="pywebview.api.hello('world').then(alert)">Say hello</button>
"""

webview.create_window('Hello API', html=html, js_api=Api())
webview.start()
```

## Where to go next

- [Usage](/guide/usage.md): basic concepts
- [Application architecture](/guide/architecture.md): how to structure your application
- [JS–Python bridge](/guide/interdomain.md): call Python from Javascript and the other way round
- [Security](/guide/security.md): what the page can access
- [Debugging](/guide/debugging.md) and [FAQ](/guide/faq.md): when something goes wrong
- [API reference](/api) and [examples](/examples)

## Contribute

Read the [contributing guidelines](/contributing/).

## About

_pywebview_ is created by [Roman Sirokov](https://github.com/r0x0r/) and is open source under the BSD license.

## Support the project

If you find _pywebview_ useful, please support it.

::: center
[![Github Sponsor](/github_sponsor_button.png)](https://github.com/sponsors/r0x0r)


[![Open Collective](/opencollective.png)](https://opencollective.com/pywebview/donate)
:::
