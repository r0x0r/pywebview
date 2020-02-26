# Toggle topmost

Switch application window to topmost mode after five seconds (window stays on top of, or in front of, other windows).

``` python
import webview
import time

def toggle_topmost(window):
    # wait a few seconds before toggling topmost:
    time.sleep(5)

    window.toggle_topmost()


if __name__ == '__main__':
    window = webview.create_window('Topmost window', 'https://pywebview.flowrl.com/hello')
    webview.start(window)
```