import webview
import threading

"""
This example demonstrates creating an open file dialog.
"""


def open_file_dialog():
    # wait until the webview window is ready:
    webview.webview_ready()

    file_types = ('Image Files (*.bmp;*.jpg;*.gif)', 'All files (*.*)')

    print(webview.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=True, file_types=file_types))


if __name__ == '__main__':
    t = threading.Thread(target=open_file_dialog)
    t.start()

    webview.create_window("Open file dialog example", "http://www.flowrl.com")
