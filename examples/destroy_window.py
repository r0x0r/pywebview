import webview
import threading
import time

"""
This example demonstrates how a webview window is created and destroyed
programmatically after 5 seconds.
"""


def destroy():
    # show the window for a few seconds before destroying it:
    time.sleep(5)

    print("Destroying window..")
    webview.destroy_window()
    print("Destroyed!")


if __name__ == '__main__':
    t = threading.Thread(target=destroy)
    t.start()
    webview.create_window("Destroy Window Example", "https://pywebview.flowrl.com/hello")
    print("Window is destroyed")
