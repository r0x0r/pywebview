"""This example demonstrates how to obtain available display information using webview.screens"""

import webview


def display_screen_info():
    screens = webview.screens
    print(f'Available screens are: {str(screens)}')


if __name__ == '__main__':
    display_screen_info()  # display screen info before starting app

    window = webview.create_window('Simple browser', 'https://pywebview.flowrl.com/hello')
    webview.start(display_screen_info)
