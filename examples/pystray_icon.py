from PIL import Image
from pystray import Icon, Menu, MenuItem
import webview

import sys
if sys.platform == 'darwin':
    # System tray icon needs to run in it's own process on Mac OS X
    from multiprocessing import Process as Thread, Queue
else:
    from threading import Thread
    from queue import Queue


"""
This example demonstrates running pywebview alongside with pystray to display a system tray icon.
"""


def run_webview():
    window = webview.create_window('Webview', 'https://pywebview.flowrl.com/hello')
    webview.start()
    return window


def run_pystray(queue: Queue):

    def on_open(icon, item):
        queue.put('open')

    def on_exit(icon, item):
        icon.stop()
        queue.put('exit')

    image = Image.open("logo/logo.png")
    menu = Menu(MenuItem('Open', on_open), MenuItem('Exit', on_exit))
    icon = Icon("Pystray", image, "Pystray", menu)
    icon.run()


if __name__ == '__main__':
    queue = Queue()
 
    icon_thread = Thread(target=run_pystray, args=(queue,))
    icon_thread.start()

    window = run_webview()

    while True:
        event = queue.get()
        if event == 'open':
            if window.closed.is_set():
                window = run_webview()
        if event == 'exit':
            if not window.closed.is_set():
                window.destroy()
            break

    icon_thread.join()
