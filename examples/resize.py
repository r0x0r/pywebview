"""Resize window."""

from time import sleep

import webview


def resize(window):
    print(f'Window size is ({window.width}, {window.height})')
    sleep(2)
    window.resize(420, 420)
    print(f'Window size is ({window.width}, {window.height})')


if __name__ == '__main__':
    window = webview.create_window(
        'Resize window example', html='<h1>Resize window</h1>', width=800, height=600
    )
    webview.start(resize, window)
