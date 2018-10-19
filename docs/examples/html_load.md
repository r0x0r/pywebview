# HTML load

Display content by loading HTML on the fly.

``` python
import webview
import threading

def load_html():
    webview.load_html('<h1>This is dynamically loaded HTML</h1>')


if __name__ == '__main__':
    t = threading.Thread(target=load_html)
    t.start()

    webview.create_window('Load HTML Example')
```