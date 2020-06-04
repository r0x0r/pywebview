# Hide / show window

Programmatically hide and show window

``` python
import webview
import time


def hide_show(window):
    time.sleep(5)
    window.hide()

    time.sleep(5)
    window.show()


if __name__ == '__main__':
    window = webview.create_window('Hide / show window', 'https://pywebview.flowrl.com/hello')
    webview.start(hide_show, window)
````
