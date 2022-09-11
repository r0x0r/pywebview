import webview
import threading

"""
This example demonstrates creating a text dialog.
"""


def open_text_dialog(window):
    result = window.create_text_dialog("Test Title", "Test message contents!")
    if result == 1:
        print("User clicked OK")
    else:
        print("User clicked Cancel")


if __name__ == '__main__':
    window = webview.create_window('Open text dialog example', 'https://pywebview.flowrl.com/hello')
    webview.start(open_text_dialog, window)
