# Toggle topmost

Switch application window to topmost mode after five seconds (window stays on top of, or in front of, other windows).

``` python
import webview
import time

def on_top(window):
    # wait a few seconds before toggling topmost:
    time.sleep(5)

    window.toggle_on_top()
    #wait a bit, then deactivate
    time.sleep(5)
    window.toggle_on_top()


if __name__ == '__main__':
    window = webview.create_window('Topmost window', 'https://pywebview.flowrl.com/hello')
    webview.start(window)
```