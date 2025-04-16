# Web engine

The following renderers are used on each platform

| Platform | Code         | Renderer | Provider                                          | Browser compatibility |
|----------|--------------|----------|---------------------------------------------------|-----------------------|
| Android  |              | WebKit   |                                                   | Ever-green Chromium   |
| GTK      | gtk          | WebKit   | WebKit2 (minimum version >2.2)                    |                       |
| macOS    |              | WebKit   | WebKit.WKWebView (bundled with OS)                |                       |
| QT       | qt           | WebKit   | QtWebEngine / QtWebKit                            |                       |
| Windows  | edgechromium | Chromium | > .NET Framework 4.6.2 and Edge Runtime installed | Ever-green Chromium   |
| Windows  | winui3       | Chromium | > Windows App Runtime installed                   | Ever-green Chromium   |
| Windows  | cef          | CEF      | CEF Python                                        | Chrome 66             |
| Windows  | mshtml       | MSHTML   | DEPRECATED  Internet Explorer MSHTML              | IE11 (Windows 10/8/7) |

On Windows renderer is chosen in the following order: `edgechromium`, `winui3`, `mshtml`. `mshtml` is the only renderer that is guaranteed to be available on any system. Edge Runtime must be installed in order to use Edge Chromium on Windows. You can download it from [here](https://developer.microsoft.com/en-us/microsoft-edge/webview2/). Distribution guidelines are found [here](https://docs.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution). Similarly, Windows App Runtime must be installed in order to use WinUI3 on Windows. You can download it from [here](https://learn.microsoft.com/en-us/windows/apps/windows-app-sdk/downloads). It can also be redistributed with your application so that users don't have to install it separately.

To change a default renderer set either `PYWEBVIEW_GUI` environment variable or  pass the rendered value to `webview.start(gui=code)` function parameter. Check for available values in the Code column from the table above.

For example to use CEF on Windows

``` bash
export PYWEBVIEW_GUI=cef
```

or

``` python
import webview
webview.start(gui='cef')
```

If you wish to pass custom settings to CEF, refer to [this example](/examples/cef.html)

To force QT on Linux systems

``` bash
export PYWEBVIEW_GUI=qt
```

or

``` python
import webview
webview.start(gui='qt')
```

## Known issues and limitations

## QtWebKit

* Debugging is not supported
