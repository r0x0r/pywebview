# Window title change

Change window title every three seconds.

``` python
import webview
import threading
import time

def change_title():
    """changes title every 3 seconds"""
    for i in range(1, 100):
        time.sleep(3)
        webview.set_title("New Title #{}".format(i))


if __name__ == '__main__':
    t = threading.Thread(target=change_title)
    t.start()

    webview.create_window('First Tile',
                          'http://pywebview.flowrl.com',
                          width=800, height=600,
                          resizable=True)
```