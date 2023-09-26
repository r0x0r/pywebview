"""Programmatically hide and show window."""

import time

import webview


def hide_show(window):
    print('Window is started hidden')

    time.sleep(5)
    print('Showing window')
    window.show()

    time.sleep(5)
    print('Hiding window')
    window.hide()

    time.sleep(5)
    print('And showing again')
    window.show()


if __name__ == '__main__':
    window = webview.create_window(
        'Hide / show window', 'https://pywebview.flowrl.com/hello', hidden=True
    )
    webview.start(hide_show, window)
