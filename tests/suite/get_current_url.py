import webview
import threading

"""
This example demonstrates creating a save file dialog.
"""

def get_current_url():
    import time
    time.sleep(5)
    print(webview.get_current_url())


if __name__ == '__main__':
    t = threading.Thread(target=get_current_url)
    t.start()

    webview.create_window("Get current URL", "http://www.flowrl.com")

