# Debugging

Debugging a _pywebview_ application has two sides: the page (Javascript, HTML, CSS) and Python. This page shows how to debug both.

## Debug mode

Set `debug=True` in `webview.start()`.

``` python
import webview

webview.create_window('Debug', 'https://pywebview.flowrl.com/hello')
webview.start(debug=True)
```

Debug mode does three things:

- It turns on the web inspector (DevTools) of the web engine and, on most platforms, opens it automatically.
- It turns on the right-click context menu, which is disabled otherwise.
- It sets the _pywebview_ log level to `debug`, unless you set `PYWEBVIEW_LOG` yourself.

To stop the inspector from opening automatically, set `webview.settings['OPEN_DEVTOOLS_IN_DEBUG'] = False` before `webview.start()`. You can still open it from the context menu.

Do not ship your application with `debug=True`.

## Web inspector by platform

| Platform | How to open the inspector |
| --- | --- |
| Windows (`edgechromium`, `winui3`) | Opens automatically. Also F12 or right click → Inspect |
| macOS | Opens automatically. Also right click → Inspect Element |
| GTK | Opens automatically in a separate inspector window |
| Qt (QtWebEngine) | Opens automatically in a separate "Web Inspector" window |
| CEF | Opens automatically |
| Android | Remote debugging, see below |

On Qt, the inspector is a web page served by the Chromium remote debugging server. _pywebview_ starts at port 8228 and uses the next free port if it is busy.

## Remote debugging

With `edgechromium`, `winui3` and `qt` you can debug from an external Chromium browser. Set the port before `webview.start()`.

``` python
webview.settings['REMOTE_DEBUGGING_PORT'] = 9222
webview.start(debug=True)
```

Then open `http://localhost:9222` in Chrome or Edge, or connect from your IDE. See the [remote debugging example](https://github.com/r0x0r/pywebview/blob/master/examples/remote_debugging.py).

## Python logs

_pywebview_ writes logs with the standard `logging` module under the logger name `pywebview`. To see debug logs, set the `PYWEBVIEW_LOG` environment variable before you start the application.

``` bash
PYWEBVIEW_LOG=debug python main.py
```

The first lines of the log show which renderer was selected. Use the log to check which backend is used, and why a backend failed to load.

To change the log format, use `webview.settings['LOG_FORMAT']`.

## Debug Python code

`webview.start()` blocks the main thread and runs your code in other threads, so debuggers need a little care.

- `print()` and `logging` in your own functions work as usual. Output from a JS API function appears in the terminal where you started the application.
- Exceptions in a JS API function do not crash the application. _pywebview_ logs them and rejects the promise in Javascript. See the error in the browser console, and its Python stack trace in `error.stack`.
- A breakpoint in a JS API function pauses only that thread. The window stays responsive.
- Errors in Javascript do not appear in the terminal. Open the web inspector to see them.

To check what the page sees, run Javascript from Python.

``` python
print(window.evaluate_js('document.readyState'))
```

## Common problems

**`pywebview.api` is `undefined`.** The page ran before the bridge was ready. Wait for the `pywebviewready` event. See [JS–Python bridge](/guide/interdomain.md#wait-for-pywebviewready). Also check that the page is [allowed to use the JS API](/guide/security.md#which-pages-get-the-js-api). _pywebview_ logs a warning when a page loses access.

**The window is blank.** On Windows, check that the [WebView2 runtime](/guide/web_engine.md) is installed. Start the application with `PYWEBVIEW_LOG=debug` and read the log. For a local page, open the inspector and check the Network tab for files that failed to load.

**The application works from source but not when frozen.** Check that your HTML, CSS and Javascript files are included in the package. See [Freezing](/guide/freezing.md).

## Android

You cannot attach a Python debugger on Android. Print messages and read them from `logcat`.

``` bash
adb -s <DEVICE_ID> logcat | grep python
```

Debug the page with [WebView remote debugging](https://developer.chrome.com/docs/devtools/remote-debugging/webviews/).
