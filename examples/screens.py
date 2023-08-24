"""This example demonstrates how to obtain available display information using webview.screens"""

import webview


def display_screen_info():
    screens = webview.screens



if __name__ == '__main__':
    screens = webview.screens
    print('Available screens are: ' + str(screens))

    window = webview.create_window('', html='placed on the first monitor', screen=screens[0])
    window = webview.create_window('', html='placed on the second monitor', screen=screens[1])

    webview.start()

