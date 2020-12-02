import webview

"""
This example demonstrates how to stop freezing main thread.
"""

if __name__ == '__main__':
    # Create a standard webview window
    window = webview.create_window('Simple browser', 'https://pywebview.flowrl.com/hello')

    webview.start(block=False)

    print('free main thread')

    # Create another webview window
    window2 = webview.create_window('Simple browser2', 'https://pywebview.flowrl.com/hello')
