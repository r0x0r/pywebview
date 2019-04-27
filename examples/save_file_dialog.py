import webview
import threading

"""
This example demonstrates creating a save file dialog.
"""


def save_file_dialog(window):
    import time
    time.sleep(5)
    result = window.create_file_dialog(webview.SAVE_DIALOG, directory='/', save_filename='test.file')
    print(result)


if __name__ == '__main__':
    window = webview.create_window('Save file dialog', 'https://pywebview.flowrl.com/hello')
    webview.start(save_file_dialog, window)