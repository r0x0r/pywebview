## Destroy window

Programmatically destroy created window after five seconds.

``` python
import webview
import threading
import time

def destroy():
    # show the window for a few seconds before destroying it:
    time.sleep(5)

    print("Destroying window..")
    webview.destroy_window()
    print("Destroyed!")


if __name__ == '__main__':
    t = threading.Thread(target=destroy)
    t.start()
    webview.create_window("Destroy Window Example", "http://pywebview.flowrl.com")
    print("Window is destroyed")
```