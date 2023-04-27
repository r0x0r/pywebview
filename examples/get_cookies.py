"""This example demonstrates how to get cookies for the current website."""

import webview


def get_cookies(window):
    cookies = window.get_cookies()
    for c in cookies:
        print(c.output())


if __name__ == "__main__":
    window = webview.create_window("Get cookies", "https://google.com")
    webview.start(get_cookies, window, private_mode=False)
