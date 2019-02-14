import webview

"""
This example demonstrates how to create a CEF window. Available only on Windows.
"""

if __name__ == '__main__':
    # Create a CEF window
    webview.config.gui = 'cef'
    webview.create_window('CEF browser', 'https://pywebview.flowrl.com/hello')
