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
    webview.windows[0].events.loaded -= on_loaded
    webview.windows[0].load_url('https://pywebview.flowrl.com/hello')


if __name__ == '__main__':
    window = webview.create_window('Simple browser', 'https://pywebview.flowrl.com/', confirm_close=True)

    window.events.closed += on_closed
    window.events.closing += on_closing
    window.events.shown += on_shown
    window.events.loaded += on_loaded
    window.events.minimized += on_minimized
    window.events.maximized += on_maximized
    window.events.restored += on_restored

    webview.start()
