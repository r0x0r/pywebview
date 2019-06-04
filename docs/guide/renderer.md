# Web engine

The following renderers are used on each platform


| Platform | Renderer | Provider                                          | Browser compatibility |
|----------|----------|---------------------------------------------------|-----------------------|
| GTK      | WebKit   | WebKit2                                           |                       |
| macOS    | WebKit   | WebKit.WKWebView (bundled with OS)                |                       |
| QT       | WebKit   | QtWebEngine / QtWebKit                            |                       |
| Windows  | MSHTML   | MSHTML via .NET / System.Windows.Forms.WebBrowser | IE11 (Windows 10/8/7) |
| Windows  | EdgeHTML | > .NET Framework 4.6.2 and Windows 10 build 17110 |                       |
| Windows  | CEF      | CEF Python                                        | Chrome 66             |


To change a default renderer set either `PYWEBVIEW_GUI` environment variable or `webview.gui` value in the code. Available values are `cef` (Windows), `qt` (Linux, macOS) and `gtk` (Linux).

For example to use CEF on Windows

``` bash
PYWEBVIEW_GUI=cef
```

or

``` python
import webview
webview.start(gui='cef')
```

To force QT on Linux systems

``` bash
PYWEBVIEW_GUI=qt
```

or

``` python
import webview
webview.start(gui='qt')
```
