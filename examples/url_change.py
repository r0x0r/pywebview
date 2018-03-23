import webview
import threading

"""
This example demonstrates how a webview window is created and URL is changed
after 10 seconds.
"""


def change_url():
    # wait until the webview window is ready:
    webview.webview_ready()

    # let the user view the window a few seconds:
    import time
    time.sleep(6)

    # change url:
    webview.load_url("http://www.html5zombo.com/")


if __name__ == '__main__':
    t = threading.Thread(target=change_url)
    t.start()

    # Create a non-resizable webview window with 800x600 dimensions
    webview.create_window("Simple browser", "http://www.google.com", width=800, height=600, resizable=True)
