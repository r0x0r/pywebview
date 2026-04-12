"""Get available display information using `webview.screens`"""

import webview

if __name__ == '__main__':
    screens = webview.screens
    print('Available screens:')

    for i, screen in enumerate(screens):
        print(f'\nScreen {i + 1}:')
        print(f'  Position: ({screen.x}, {screen.y})')
        print(f'  Size: {screen.width}x{screen.height}')
        print(f'  Scale: {screen.scale}x')
        print(f'  DPI: {screen.dpi}')
        print(f'  Physical Size: {screen.physical_width}x{screen.physical_height}')

        webview.create_window('', html=f'placed on the monitor {i + 1}', screen=screen)

    webview.start()
