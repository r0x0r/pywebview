# Fullscreen window

Create a fullscreen window.

``` python
import webview


if __name__ == '__main__':
    webview.create_window('Full-screen window',
                          'https://pywebview.flowrl.com/hello',
                          fullscreen=True)
    webview.start()
```