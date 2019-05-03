import webview

"""
This example demonstrates how to get the current url loaded in the webview.
"""


def get_current_url(window):
    print(window.get_current_url())


if __name__ == '__main__':
    window = webview.create_window('Get current URL', 'https://pywebview.flowrl.com/hello')
    webview.start(get_current_url, window)
