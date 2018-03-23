import webview
import threading

"""
This example demonstrates how a webview window is created and destroyed
programmatically after 5 seconds
"""


def destroy():
    # wait until the webview window is ready:
    webview.webview_ready()

    # let the user view the window a few seconds:
    import time
    time.sleep(4)

    print("Destroying window..")
    webview.destroy_window()
    print("Destroyed!")


if __name__ == '__main__':
    t = threading.Thread(target=destroy)
    t.start()
    webview.create_window("Simple browser", "http://www.google.com")
    print("Window is destroyed")
