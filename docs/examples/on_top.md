# Topmost window

Create a window that stays on top of, or in front of, other windows.

``` python
import pywebview
import time

def deactivate(window):
    #window starts on top and is changed later
    time.sleep(5)
    window.on_top = False


if __name__ == '__main__':
    # Create webview window that stays on top of, or in front of, all other windows
    window = webview.create_window('Topmost window',
                          'https://pywebview.flowrl.com/hello',
                          on_top=True)
    webview.start(deactivate, window)
```