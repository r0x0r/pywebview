import webview

"""
This example demonstrates how to create a full-screen webview window.
"""

if __name__ == '__main__':
    # Create a non-resizable webview window with 800x600 dimensions
    webview.create_window('Full-screen window',
                          'https://pywebview.flowrl.com/hello',
                          fullscreen=True)
    webview.start()
