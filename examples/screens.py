"""Get available display information using `webview.screens`"""

import webview



if __name__ == '__main__':
    screens = webview.screens
    print('Available screens are: ' + str(screens))

    for i, screen in enumerate(screens):
        webview.create_window('', html=f'placed on the monitor {i+1}', screen=screen)

    webview.start()

