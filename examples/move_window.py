"""Set window coordinates and move window after its creation."""

from time import sleep

import webview


def move(window):
    print('Window coordinates are ({0}, {1})'.format(window.x, window.y))

    sleep(2)
    window.move(200, 200)
    sleep(1)
    print('Window coordinates are ({0}, {1})'.format(window.x, window.y))


if __name__ == '__main__':
    window = webview.create_window('Move window example', html='<h1>Move window</h1>', x=0, y=0)
    webview.start(move, window)
