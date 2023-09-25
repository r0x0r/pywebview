"""
Create a pywebview windows using QT (normally GTK is preferred)
"""

import webview

if __name__ == '__main__':
    # Create a non-resizable webview window with 800x600 dimensions
    webview.create_window('Qt Example', 'http://flowrl.com')
    webview.start(gui='qt')
