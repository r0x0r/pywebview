import webview
import threading

"""
This example demonstrates how a webview window is created and destroyed programmatically after 5 seconds
"""

def destroy():
    import time
    time.sleep(5)
    print("Destroying window..")
    webview.destroy_window()


if __name__ == '__main__':
    t = threading.Thread(target=destroy)
    t.start()
    webview.create_window("Simple browser", "http://www.google.com")
    print("Window is destroyed")
