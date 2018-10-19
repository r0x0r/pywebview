# Fullscreen window

Create a fullscreen window.

``` python
import webview


if __name__ == '__main__':
    # Create a non-resizable webview window with 800x600 dimensions
    webview.create_window("Full-screen browser",
                          "http://pywebview.flowrl.com",
                          fullscreen=True)
```