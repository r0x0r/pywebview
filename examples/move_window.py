import webview
from time import sleep

"""
This example demonstrates how to load HTML in a web view window
"""


def move(window):
    sleep(2)
    window.move(0, 0)


if __name__ == '__main__':
    window = webview.create_window('Move window example', html='<h1>Move window</h1>', x=100, y=200)
    webview.start(move, window)
