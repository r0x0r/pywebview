# Debugging

To debug Javascript, set the `debug` parameter of `start` to `True`

``` python
import webview

webview.create_window('https://pywebview.flowrl.com/hello')
webview.start(debug=True)
```

This will enable web inspector on macOS, GTK and QT (QTWebEngine only). To open the web inspector, right click on the page and select Inspect.

To debug EdgeHTML, you need to install [Microsoft Edge DevTools Preview](https://www.microsoft.com/en-us/p/microsoft-edge-devtools-preview/9mzbfrmz0mnj). Launch the application and select your application from the list of running WebViews. The `debug` flag also routes `console.logs` to the Python console.

There is no way to attach an external debugger to MSHTML. The `debug` flag enables Javascript error reporting and right-click context menu on Windows.

