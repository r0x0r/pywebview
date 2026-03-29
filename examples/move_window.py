"""Set window coordinates and move window after its creation."""

from time import sleep

import webview


def move(window):
    print(f'Window coordinates are ({window.x}, {window.y})')
    print(f'Window dimensions are ({window.width}x{window.height})')

    # Get the primary screen to calculate relative position
    screens = webview.screens
    if screens:
        primary_screen = screens[0]
        print(f'Primary screen: {primary_screen.width}x{primary_screen.height}')

        # Move to bottom-right area of screen (with some padding)
        new_x = primary_screen.width - window.width - 100
        new_y = primary_screen.height - window.height - 100
    else:
        # Fallback to absolute coordinates
        new_x, new_y = 500, 500

    sleep(2)
    window.move(new_x, new_y)
    sleep(1)
    print(f'Window coordinates are now ({window.x}, {window.y})')


if __name__ == '__main__':
    window = webview.create_window('Move window example', html='<h1>Move window</h1>', x=300, y=300)
    webview.start(move, window)
