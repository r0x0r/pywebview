import webview
import time

"""
This example demonstrates how a webview window is created and URL is changed
after 10 seconds.
"""


def change_url(window):
    # wait a few seconds before changing url:
    time.sleep(10)

    # change url:
    window.load_url('https://pywebview.flowrl.com/hello')


if __name__ == '__main__':
    window = webview.create_window('URL Change Example', 'http://www.google.com')
    webview.start(change_url, window)
