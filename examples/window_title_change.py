"""Change window title every three seconds."""

import time

import webview


def change_title(window):
    """changes title every 3 seconds"""
    for i in range(1, 100):
        time.sleep(3)
        window.title = f'New Title #{i}'
        print(window.title)


if __name__ == '__main__':
    window = webview.create_window('Change title example', 'https://pywebview.flowrl.com/hello')
    webview.start(change_title, window)
