# Usage

The bare minimum to get pywebview started is

``` python
import webview
webview.create_window("It works, Jim!", "http://pywebview.flowrl.com")
```

The second argument `url` can point to either to a remote a local url, a local path or be left empty. If empty, you can load HTML using a `load_html` function. E.g.

``` python
def load_html():
    webview.load_html('<h1>This is dynamically loaded HTML</h1>')


if __name__ == '__main__':
    t = threading.Thread(target=load_html)
    t.start()

    webview.create_window('Load HTML example')
```

Note that `webview.create_window` blocks the main thread execution, so other code has to be run on a separate thread.
