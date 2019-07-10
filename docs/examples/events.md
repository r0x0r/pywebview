## Events

Subscribe and unsubscribe to pywebview events.


``` python
import webview
import time


def on_shown():
    print('pywebview window shown')

def on_loaded():
    print('DOM is ready')

    # unsubscribe event listener
    webview.windows[0].loaded -= on_loaded
    webview.windows[0].load_url('https://google.com')

if __name__ == '__main__':
    # Create a standard webview window
    window = webview.create_window('Simple browser', 'https://pywebview.flowrl.com/hello')
    window.shown += on_shown
    window.loaded += on_loaded
    webview.start()
```