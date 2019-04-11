# Debugging

To debug Javascript, set the `debug` parameter to `True`

``` python
import webview

webview.create_window('https://pywebview.flowrl.com', debug=True)
```

This will enable web inspector on macOS, GTK and QT (QTWebEngine only). To open the web inspector, right click on the page and select Inspect. Unfortunately the Trident web engine on Windows has no web inspector and currently there is no way to attach an external debugger. The `debug` flag enables Javascript error reporting and right-click context menu on Windows.

You can debug Python code normally using your favorite debugger.
