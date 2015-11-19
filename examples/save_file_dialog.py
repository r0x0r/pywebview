import webview
import threading

"""
This example demonstrates creating a save file dialog.
"""

def save_file_dialog():
    import time
    time.sleep(5)
    print(webview.create_file_dialog(webview.SAVE_DIALOG))


if __name__ == '__main__':
    t = threading.Thread(target=save_file_dialog)
    t.start()

    webview.create_window("Save file dialog", "http://www.flowrl.com")

