import webview

"""
This example demonstrates how to load CSS in a web view window
"""


def load_css(window):
    window.load_css('body { background: red !important; }')


if __name__ == '__main__':
    window = webview.create_window('Load CSS Example', 'https://pywebview.flowrl.com/hello')
    webview.start(load_css, window)