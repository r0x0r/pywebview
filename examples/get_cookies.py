import webview

"""
This example demonstrates how to get cookies for the current website
"""


def get_cookies(window):
    cookies = window.get_cookies()
    print(cookies)


if __name__ == '__main__':
    window = webview.create_window('Get cookies', 'https://google.com')
    webview.start(get_cookies, window, private_mode=False)
