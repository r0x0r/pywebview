import webview

"""
This example demonstrates how to enable debugging of webview content. To open
up debugging console, right click on an element and select Inspect.
"""

if __name__ == '__main__':
    webview.create_window('Debug window', 'https://pywebview.flowrl.com/hello')
    webview.start(debug=True)
