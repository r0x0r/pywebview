# Toggle full-screen

Switch application window to a full-screen mode after five seconds.

``` python
import webview
import threading
import time


def toggle_fullscreen():
    # wait a few seconds before toggle fullscreen:
    time.sleep(5)

    webview.toggle_fullscreen()


if __name__ == '__main__':
    t = threading.Thread(target=toggle_fullscreen)
    t.start()

    webview.create_window("Full-screen window", "https://pywebview.flowrl.com/hello")
```