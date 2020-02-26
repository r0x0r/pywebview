# Topmost window

Create a window that stays on top of, or in front of, other windows.

``` python
import webview


if __name__ == '__main__':
    webview.create_window('Topmost window',
                          'https://pywebview.flowrl.com/hello',
                          topmost=True)
    webview.start()
```