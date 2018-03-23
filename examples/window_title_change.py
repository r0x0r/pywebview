import webview
import threading
import time

'''
This example demonstrates how to change a window title.
'''


def change_title():
    # change title every 3 seconds:
    for i in range(1, 100):
        webview.set_title("New Title #{}".format(i))
        time.sleep(3)


if __name__ == '__main__':
    t = threading.Thread(target=change_title)
    t.start()

    webview.create_window('Simple browser', 'http://www.flowrl.com', width=800, height=600, resizable=True)
