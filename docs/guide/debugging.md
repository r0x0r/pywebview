# Debugging

To debug Javascript, set the `debug` parameter of `start` to `True`

``` python
import webview

webview.create_window('Woah dude!', 'https://pywebview.flowrl.com/hello')
webview.start(debug=True)
```

This will enable web inspector on macOS, GTK and QT (QTWebEngine only). To open the web inspector on macOS, right click on the page and select Inspect.


There is no way to attach an external debugger to MSHTML. The `debug` flag enables Javascript error reporting and right-click context menu on Windows.
