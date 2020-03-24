import webview
import time

"""
This example demonstrates how to toggle topmost mode programmatically.
"""


def on_top(window):
    # wait a few seconds before toggle topmost:
    time.sleep(5)

    window.toggle_on_top()
    time.sleep(5)
    #wait a bit then deactivate
    window.toggle_on_top()

if __name__ == '__main__':
    window = webview.create_window('Topmost window', 'https://pywebview.flowrl.com/hello')
    webview.start(on_top, window)
