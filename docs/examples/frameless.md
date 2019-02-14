# Frameless window

Create a frameless window. The window can be moved around by dragging any point.

``` python
import webview


if __name__ == '__main__':
    # Create a non-resizable webview window with 800x600 dimensions
    webview.create_window("Frameless window",
                          "https://pywebview.flowrl.com/hello",
                          fullscreen=True)
```