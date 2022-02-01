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


def on_minimized():
    print('pywebview window minimized')


def on_restored():
    print('pywebview window restored')


def on_maximized():
    print('pywebview window maximized')


def on_loaded():
    print('DOM is ready')

    # unsubscribe event listener
    webview.windows[0].on_loaded -= on_loaded
    webview.windows[0].load_url('https://pywebview.flowrl.com/hello')


if __name__ == '__main__':
    window = webview.create_window('Simple browser', 'https://pywebview.flowrl.com/', confirm_close=True)

    window.on_closed += on_closed
    window.on_closing += on_closing
    window.on_shown += on_shown
    window.on_loaded += on_loaded
    window.on_minimized += on_minimized
    window.on_maximized += on_maximized
    window.on_restored += on_restored

    webview.start()
