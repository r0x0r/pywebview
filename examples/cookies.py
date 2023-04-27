"""This example demonstrates how to use cookies and local storage."""

import webview


def read_cookies(window):
    # set a cookie in the application window for this object not to be empty
    print(window.get_cookies())


if __name__ == "__main__":
    window = webview.create_window("Cookie example", "assets/cookies.html")
    webview.start(read_cookies, window, private_mode=False)
