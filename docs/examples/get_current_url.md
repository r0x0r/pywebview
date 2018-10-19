# Get current URL

Print current URL after page is loaded.

``` python
import webview
import threading


def get_current_url():
    print(webview.get_current_url())


if __name__ == '__main__':
    t = threading.Thread(target=get_current_url)
    t.start()

    webview.create_window("Get current URL", "http://pywebview.flowrl.com")
```