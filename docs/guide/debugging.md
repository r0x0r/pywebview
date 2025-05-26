# Debugging

To debug Javascript, set `webview.start(debug=True)`.

``` python
import webview

webview.create_window('Woah dude!', 'https://pywebview.flowrl.com/hello')
webview.start(debug=True)
```

This will enable web inspector on macOS, GTK and QT (QTWebEngine only). To open the web inspector on macOS, right click on the page and select Inspect. To disable auto-opening of DevTools, set `webview.settings['OPEN_DEVTOOLS_IN_DEBUG'] = False` before invoking `webview.start()`.

Debugging Python code on Android is not possible apart from printing message to `logcat`. Use `adb -s <DEVICE_ID> logcat | grep python` for displaying log messages related to Python. Frontend code can be debugged with WebView remote debugging. Refer to [this guide](https://developer.chrome.com/docs/devtools/remote-debugging/webviews/) for details.

Remote debugging is supported with the `edgechromium` renderer. To take remote debugging into use set `webview.settings['REMOTE_DEBUGGING_PORT']` to the port number you wish to run a debugger on.

There is no way to attach an external debugger to MSHTML. The `debug` flag enables Javascript error reporting and right-click context menu.

To turn on debug logging for `pywebiew` itself, set `PYWEBVIEW_LOG=debug` environment variable before starting the application.