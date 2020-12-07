from PIL import Image
from pystray import Icon, Menu, MenuItem
import webview
import sys

if sys.platform == 'darwin':
    raise NotImplementedError('This example does not work on macOS.')
    
from threading import Thread
from queue import Queue


"""
This example demonstrates running pywebview alongside with pystray to display a system tray icon.
"""


def run_webview():
    window = webview.create_window('Webview', 'https://pywebview.flowrl.com/hello')
    webview.start()


def run_pystray(queue: Queue):

    def on_open(icon, item):
        queue.put('open')

    def on_exit(icon, item):
        icon.stop()
        queue.put('exit')

    image = Image.open('logo/logo.png')
    menu = Menu(MenuItem('Open', on_open), MenuItem('Exit', on_exit))
    icon = Icon('Pystray', image, "Pystray", menu)
    icon.run()


if __name__ == '__main__':
    queue = Queue()
 
    icon_thread = Thread(target=run_pystray, args=(queue,))
    icon_thread.start()

    run_webview()

    while True:
        event = queue.get()
        if event == 'open':
            run_webview()
        if event == 'exit':
            break

    icon_thread.join()
