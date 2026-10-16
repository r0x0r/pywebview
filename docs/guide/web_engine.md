# Web engine

The following renderers are used on each platform

| Platform | Code         | Renderer | Provider                                          | Browser compatibility |
|----------|--------------|----------|---------------------------------------------------|-----------------------|
| Android  |              | WebKit   |                                                   | Ever-green Chromium   |
| GTK      | gtk          | WebKit   | WebKit2 (minimum version >2.2)                    |                       |
| macOS    |              | WebKit   | WebKit.WKWebView (bundled with OS)                |                       |
| QT       | qt           | WebKit   | QtWebEngine / QtWebKit                            |                       |
| Windows  | edgechromium | Chromium | .NET 6.0+ or .NET Framework 4.6.2+, and Edge Runtime installed | Ever-green Chromium   |
| Windows  | winui3       | Chromium | > `pywebview[winui3]` extra, Edge Runtime and Windows App Runtime installed | Ever-green Chromium   |
| Windows  | cef          | CEF      | CEF Python                                        | Chrome 66             |
| Windows  | mshtml       | MSHTML   | DEPRECATED  Internet Explorer MSHTML              | IE11 (Windows 10/8/7) |

On Windows the default renderer is chosen in the following order: `edgechromium`, `mshtml`, `winui3`. Edge Chromium and MSHTML are provided by the WinForms backend; WinUI 3 is used automatically when WinForms cannot be loaded, or it can be selected explicitly using the `winui3` code. `mshtml` is the only renderer that is guaranteed to be available on any system. Edge Runtime must be installed in order to use Edge Chromium on Windows. You can download the [WebView2 Runtime](https://developer.microsoft.com/en-us/microsoft-edge/webview2/), and consult its [distribution guidelines](https://docs.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution). WinUI 3 hosts the same WebView2 control as `edgechromium`, so it requires the Edge Runtime too, in addition to the Windows App Runtime. Windows App Runtime can be downloaded from the [Windows App SDK downloads page](https://learn.microsoft.com/en-us/windows/apps/windows-app-sdk/downloads) or redistributed with your application so that users don't have to install it separately.

To change a default renderer set either `PYWEBVIEW_GUI` environment variable or  pass the rendered value to `webview.start(gui=code)` function parameter. Check for available values in the Code column from the table above.

On Windows pywebview loads pythonnet on .NET (coreclr) when a runtime is available, and falls back to .NET Framework otherwise. To choose explicitly, set `PYTHONNET_RUNTIME` to `coreclr` or `netfx`.

.NET Framework needs no configuration for this — WinForms is part of the framework itself. On .NET (Core) it is not: WinForms lives in the `Microsoft.WindowsDesktop.App` shared framework, and a runtimeconfig is how it is selected. Without one, the runtime starts without WinForms and loading `System.Windows.Forms` fails.

pywebview therefore ships `webview/lib/pywebview-runtimeconfig.json`, a standard .NET runtimeconfig requesting that framework and rolling forward to whichever major is installed. An application shipping its own private .NET can point `PYTHONNET_CORECLR_RUNTIME_CONFIG` at its own file instead; pywebview leaves both variables alone when they are already set. Set them before pywebview initialises a GUI — backend selection happens on the first `webview.start()`, so before `import webview` is the safe rule.

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
