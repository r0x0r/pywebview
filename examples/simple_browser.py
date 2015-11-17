import webview

"""
This example demonstrates how to create a webview window.
"""

if __name__ == '__main__':
    # Create a non-resizable webview window with 800x600 dimensions
    webview.create_window("Simple browser", "http://www.flowrl.com", width=800, height=600, resizable=True)

