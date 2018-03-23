import webview
import threading

"""
This example demonstrates how to create and manage multiple windows
"""


def create_new_window():
    # Create new window and store its uid
    child_window = webview.create_window('Window #2', width=800, height=400)

    # Load content into both windows
    webview.load_html('<h1>Master Window</h1>')
    webview.load_html('<h1>Child Window</h1>', uid=child_window)


if __name__ == '__main__':
    t = threading.Thread(target=create_new_window)
    t.start()

    # Master window
    webview.create_window('Window #1', width=800, height=600)
