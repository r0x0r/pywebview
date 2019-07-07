# Use CEF

To use Chrome Embedded Framework on Windows.

``` python
import webview


if __name__ == '__main__':
    webview.create_window('CEF Example', 'https://pywebview.flowrl.com/hello')
    webview.start(gui='cef')
```
