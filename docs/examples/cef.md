# Use CEF

To use Chrome Embedded Framework on Windows.

``` python
import webview


if __name__ == '__main__':
    webview.gui = 'cef'
    webview.create_window('CEF Example', 'https://pywebview.flowrl.com/hello')
```