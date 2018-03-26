import webview
import threading

"""
This example demonstrates how to load HTML in a web view window
"""


def load_html():
    webview.load_html('<h1>This is dynamically loaded HTML</h1>')

if __name__ == '__main__':
    t = threading.Thread(target=load_html)
    t.start()

    webview.create_window('Load HTML Example')
