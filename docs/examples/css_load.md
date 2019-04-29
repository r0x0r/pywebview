# CSS load

Change window background color by loading CSS

``` python
import webview


def load_css(window):
    window.load_css('body { background: red !important; }')


if __name__ == '__main__':
    window = webview.create_window('Load CSS Example', 'https://pywebview.flowrl.com/hello')
    webview.start(load_css, window)

```