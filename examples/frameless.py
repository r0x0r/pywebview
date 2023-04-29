"""This example demonstrates how to create a frameless window with a custom minimum size."""

import webview

if __name__ == '__main__':
    # Create a resizable webview window with minimum size constraints
    webview.create_window('Frameless window', 'http://pywebview.flowrl.com/hello', frameless=True)
    webview.start()
