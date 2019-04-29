import webview
import time

"""
This example demonstrates how a webview window is created and destroyed
programmatically after 5 seconds.
"""


def destroy(window):
    # show the window for a few seconds before destroying it:
    time.sleep(5)
    print('Destroying window..')
    window.destroy()
    print('Destroyed!')


if __name__ == '__main__':
    window = webview.create_window('Destroy Window Example', 'https://pywebview.flowrl.com/hello')
    webview.start(destroy, window)
    print('Window is destroyed')
