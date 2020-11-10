import webview

"""
This example demonstrates how to stop freezing main thread.
"""

if __name__ == '__main__':
    # Create a standard webview window
    window = webview.create_window('Tab1', 'https://pywebview.flowrl.com/')
    process = webview.start(block=False)
    print('free main thread')
    window2 = webview.create_window('Tab2', 'https://pywebview.flowrl.com/hello')
    process.join()
    # blocked main thread
