import webview
import threading
import time

"""
This example demonstrates how to toggle fullscreen mode programmatically.
"""


def toggle_fullscreen(window):
    # wait a few seconds before toggle fullscreen:
    time.sleep(5)

    window.toggle_fullscreen()


if __name__ == '__main__':
    window = webview.create_window('Full-screen window', 'https://pywebview.flowrl.com/hello')
    webview.start(toggle_fullscreen, window)
