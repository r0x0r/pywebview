import webview
import threading

"""
In this example demonstrates a webview window is created and after 10 seconds URL is changed.
"""

def change_url():
    import time
    time.sleep(10)
    webview.load_url("http://www.html5zombo.com/")


if __name__ == '__main__':
    t = threading.Thread(target=change_url)
    t.start()

    # Create a non-resizable webview window with 800x600 dimensions
    webview.create_window("Simple browser", "http://www.flowrl.com", width=800, height=600, resizable=True)

