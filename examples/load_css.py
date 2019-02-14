import webview
import threading

"""
This example demonstrates how to load CSS in a web view window
"""


def load_css():
    webview.load_css('body { background: red !important; }')


if __name__ == '__main__':
    t = threading.Thread(target=load_css)
    t.start()

    webview.create_window('Load CSS Example', 'https://pywebview.flowrl.com/hello')
