import webview
import threading

"""
This example demonstrates how to toggle fullscreen mode programmatically.
"""


def toggle_fullscreen():
    # wait until the webview window is ready:
    webview.webview_ready()

    # let the user view the window a few seconds:
    import time
    time.sleep(4)

    webview.toggle_fullscreen()


if __name__ == '__main__':
    t = threading.Thread(target=toggle_fullscreen)
    t.start()

    webview.create_window("Full-screen window", "http://www.flowrl.com")
