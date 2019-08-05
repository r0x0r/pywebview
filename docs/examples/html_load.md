# HTML load

Display content by loading HTML on the fly.

``` python
import webview
import time


def load_html(window):
    time.sleep(5)
    window.load_html('<h1>This is dynamically loaded HTML</h1>')


if __name__ == '__main__':
    window = webview.create_window('Load HTML Example', html='<h1>This is initial HTML</h1>')
    webview.start(load_html, window)
```
