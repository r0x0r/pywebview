import webview
import threading

'''
This example demonstrates how to change a window title.
'''


def change_url():
    webview.set_title('New title')


if __name__ == '__main__':
    t = threading.Thread(target=change_url)
    t.start()

    webview.create_window('Simple browser', 'http://www.flowrl.com', width=800, height=600, resizable=True)

