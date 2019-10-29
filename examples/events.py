import webview
import time
"""
This example demonstrates how to handle pywebview events.
"""

def on_closed():
    print('pywebview window is closed')


def on_closing():
    print('pywebview window is closing')


def on_shown():
    print('pywebview window shown')


def on_loaded():
    print('DOM is ready')

    # unsubscribe event listener
    webview.windows[0].loaded -= on_loaded
    webview.windows[0].load_url('https://pywebview.flowrl.com/hello')


if __name__ == '__main__':
    window = webview.create_window('Simple browser', 'https://pywebview.flowrl.com/', confirm_close=True)
    window.closed += on_closed
    window.closing += on_closing
    window.shown += on_shown
    window.loaded += on_loaded
    webview.start()
