import webview
import threading

"""
This example demonstrates how a webview window is created and URL is changed after 10 seconds.
"""

def change_url():
    import time
    time.sleep(10)
    webview.load_url("http://www.html5zombo.com/")


if __name__ == '__main__':
    t = threading.Thread(target=change_url)
    t.start()

    # Create a non-resizable webview window with 800x600 dimensions
    webview.create_window("Simple browser", "http://www.google.com", width=800, height=600, resizable=True)

