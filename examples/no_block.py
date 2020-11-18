import webview
import multiprocessing
import sys


if getattr(sys, 'frozen', False):
    multiprocessing.freeze_support()


def create_window():
    window = webview.create_window('Simple browser', 'https://pywebview.flowrl.com/hello')
    webview.start()


if __name__ == '__main__':
    multiprocessing.set_start_method('spawn')
    p = multiprocessing.Process(target=create_window)
    p.start()

    print('Main thread is not blocked. You can execute your code after pywebview window is created')

    # main thread must be blocked using join or any other user defined method to prevent app from quitting
    p.join()
    print('App exists now')