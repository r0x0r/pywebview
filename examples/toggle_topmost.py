import webview
import time

"""
This example demonstrates how to toggle topmost mode programmatically.
"""


def toggle_topmost(window):
    # wait a few seconds before toggle topmost:
    time.sleep(5)

    window.toggle_topmost()


if __name__ == '__main__':
    window = webview.create_window('Topmost window', 'https://pywebview.flowrl.com/hello')
    webview.start(toggle_topmost, window)
