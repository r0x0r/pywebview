import webview

"""
This example demonstrates how to create a topmost webview window.
"""

if __name__ == '__main__':
    # Create webview window that stays on top of, or in front of, all other windows
    webview.create_window('Topmost window',
                          'https://pywebview.flowrl.com/hello',
                          topmost=True)
    webview.start()
