import webview
from time import sleep

"""
This example demonstrates how to minimize and restore window programmatically
"""


def minimize(window):
    print('Window is started minimized')

    sleep(5)
    print('Restoring window')
    window.restore()

    sleep(5)
    print('Minimizing window')
    window.minimize()


if __name__ == '__main__':
    window = webview.create_window('Minimize window example', html='<h1>Minimize window</h1>', minimized=True)
    webview.start(minimize, window)
