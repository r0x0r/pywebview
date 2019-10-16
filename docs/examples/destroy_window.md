## Destroy window

Programmatically destroy created window after five seconds.

``` python
import webview
import time


def destroy(window):
    # show the window for a few seconds before destroying it:
    time.sleep(5)
    print('Destroying window..')
    window.destroy()
    print('Destroyed!')


if __name__ == '__main__':
    window = webview.create_window('Destroy Window Example', 'https://pywebview.flowrl.com/hello')
    webview.start(destroy, window)
    print('Window is destroyed')
```