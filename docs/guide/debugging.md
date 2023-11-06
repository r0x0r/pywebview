# Debugging

To debug Javascript, set the `debug` parameter of `start` to `True`

``` python
import webview

webview.create_window('Woah dude!', 'https://pywebview.flowrl.com/hello')
webview.start(debug=True)
```

This will enable web inspector on macOS, GTK and QT (QTWebEngine only) and opens DevTools automatically on your application start. To disable automatic opening of DevTools you can set `webview.settings['OPEN_DEVTOOLS_IN_DEBUG'] = False`.

Debugging Python code on Android is not possible apart from printing message to `logcat`. Use `adb -s <DEVICE_NAME> logcat | grep python` for displaying log messages related to Python. Frontend code can be debugged with WebView remote debugging. Refer to [this guide](https://developer.chrome.com/docs/devtools/remote-debugging/webviews/) for details.

There is no way to attach an external debugger to MSHTML. The `debug` flag enables Javascript error reporting and right-click context menu.
