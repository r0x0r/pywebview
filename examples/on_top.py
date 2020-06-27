import webview
import time

"""
This example demonstrates how to create a topmost webview window.
"""

def deactivate(window):
    #window starts on top and is changed later
    time.sleep(5)
    window.on_top = False


if __name__ == '__main__':
    # Create webview window that stays on top of, or in front of, all other windows
    window = webview.create_window('Topmost window',
                          'https://pywebview.flowrl.com/hello',
                          on_top=True)
    webview.start(deactivate, window)
