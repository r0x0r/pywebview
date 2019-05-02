import webview


"""
This example demonstrates how to load HTML in a web view window
"""


def load_html(window):
    window.load_html('<h1>This is dynamically loaded HTML</h1>')


if __name__ == '__main__':
    window = webview.create_window('Load HTML Example', '<h1>This is initial HTML</h1>')
    webview.start(load_html, window)
