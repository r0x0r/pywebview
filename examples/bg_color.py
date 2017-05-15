import webview

"""
This example demonstrates a webview window with a custom background color that is displayed while
webview is being loaded
"""

if __name__ == '__main__':
    webview.create_window('Background color', 'http://www.flowrl.com', background_color='#FF0000')

