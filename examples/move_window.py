import webview
from time import sleep

"""
This example demonstrates how to move window programmatically
"""


def move(window):
    print('Window coordinates are ({0}, {1})'.format(window.x, window.y))

    sleep(2)
    window.move(200, 200)

    print('Window coordinates are ({0}, {1})'.format(window.x, window.y))



if __name__ == '__main__':
    window = webview.create_window('Move window example', html='<h1>Move window</h1>', x=100, y=100)
    webview.start(move, window)
