# Change URL

Change URL ten seconds after the first URL is loaded.

``` python
import webview
import time


def change_url(window):
    # wait a few seconds before changing url:
    time.sleep(10)

    # change url:
    window.load_url('https://woot.fi')


if __name__ == '__main__':
    window = webview.create_window('URL Change Example', 'https://pywebview.flowrl.com/hello'')
    webview.start(change_url, window)
```
