import webview
import threading
import time

"""
This example demonstrates how a webview window is created and URL is changed
after 10 seconds.
"""


def change_url():
    # wait a few seconds before changing url:
    time.sleep(10)

    # change url:
    webview.load_url("http://pywebview.flowrl.com")


if __name__ == '__main__':
    t = threading.Thread(target=change_url)
    t.start()

    # Create a non-resizable webview window with 800x600 dimensions
    webview.create_window("URL Change Example",
                          "http://www.google.com",
                          width=800, height=600,
                          resizable=True)
