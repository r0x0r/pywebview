# Web engine

The following renderers are used on each platform


| Platform | Renderer | Provider                                          | Browser compatibility |
|----------|----------|---------------------------------------------------|-----------------------| 
| GTK      | WebKit   | WebKit2                                           |                       |
| macOS    | WebKit   | WebKit.WKWebView (bundled with OS)                |                       |
| QT       | WebKit   | QtWebKit                                          |                       |
| Windows  | Trident  | MSHTML via .NET / System.Windows.Forms.WebBrowser | IE11 (Windows 10/8/7) |
| Windows  | CEF      | CEF Python                                        | Chrome 66             |