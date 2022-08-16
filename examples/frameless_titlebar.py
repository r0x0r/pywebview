import webview
import threading
import time

"""
This example demonstrates how to set titlebar visible in frameless (macos).
set titlebar_visible True and set frameless True, window will have titlebar and draggable
"""

def load_css(window):
    window.load_css('body { background: #eee !important; }')


if __name__ == '__main__':
    window = webview.create_window('set titlebar visible on frameless', 
    'https://pywebview.flowrl.com/hello',
     frameless=True,
     titlebar_visible=True,
     easy_drag=False)
    webview.start(load_css,window)