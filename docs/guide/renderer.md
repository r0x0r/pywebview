# Web engine

The following renderers are used on each platform


| Platform | Renderer | Provider                                          | Browser compatibility |
|----------|----------|---------------------------------------------------|-----------------------|
| GTK      | WebKit   | WebKit2                                           |                       |
| macOS    | WebKit   | WebKit.WKWebView (bundled with OS)                |                       |
| QT       | WebKit   | QtWebKit                                          |                       |
| Windows  | Trident  | MSHTML via .NET / System.Windows.Forms.WebBrowser | IE11 (Windows 10/8/7) |
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


# Known issues and limitations

## GTK WebKit2

* Versions of WebKit2 older than 2.2 has a limitation of 1000 characters of the Javascript result returned by `evaluate_js`. `get_elements` is not supported for this reason.

## QtWebKit

* Debugging is not supported


## EdgeHTML

* `file://` URLs are not fully supported. While such URLs can be loaded (via a workaround), associated resources such as images or stylesheets cannot.
* Destroying a window via `window.close()` and starting a new instance will crash the program.


