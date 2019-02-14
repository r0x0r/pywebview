import webview
import threading
import time

"""
This example demonstrates how to toggle fullscreen mode programmatically.
"""


def toggle_fullscreen():
    # wait a few seconds before toggle fullscreen:
    time.sleep(5)

    webview.toggle_fullscreen()


if __name__ == '__main__':
    t = threading.Thread(target=toggle_fullscreen)
    t.start()

    webview.create_window("Full-screen window", "https://pywebview.flowrl.com/hello")
