import webview
import threading

"""
This example demonstrates how to get the current url loaded in the webview.
"""


def get_current_url():
    print(webview.get_current_url())


if __name__ == '__main__':
    t = threading.Thread(target=get_current_url)
    t.start()

    webview.create_window("Get current URL", "http://pywebview.flowrl.com")
