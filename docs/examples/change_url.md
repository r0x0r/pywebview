# Change URL

Change URL ten seconds after the first URL is loaded.

``` python
import webview
import time


def change_url(window):
    # wait a few seconds before changing url:
    time.sleep(10)

    # change url:
    window.load_url('https://pywebview.flowrl.com/hello')


if __name__ == '__main__':
    window = webview.create_window('URL Change Example', 'http://www.google.com')
    webview.start(change_url, window)
```
