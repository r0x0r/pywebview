import webview

"""
This example demonstrates how to create a pywebview windows using QT
(normally GTK is preferred)
"""

if __name__ == '__main__':
    webview.config.use_qt = True

    # Create a non-resizable webview window with 800x600 dimensions
    webview.create_window("Simple browser", "http://flowrl.com")
