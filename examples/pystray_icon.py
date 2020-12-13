from PIL import Image
from pystray import Icon, Menu, MenuItem
import webview
import sys
import multiprocessing

if sys.platform == 'darwin':
    ctx = multiprocessing.get_context('spawn')
    Process = ctx.Process
    Queue = ctx.Queue
else:
    Process = multiprocessing.Process
    Queue = multiprocessing.Queue


"""
This example demonstrates running pywebview alongside with pystray to display a system tray icon.
"""


webview_process = None


def run_webview():
    window = webview.create_window('Webview', 'https://pywebview.flowrl.com/hello')
    webview.start()


if __name__ == '__main__':

    def start_webview_process():
        global webview_process
        webview_process = Process(target=run_webview)
        webview_process.start()

    def on_open(icon, item):
        global webview_process
        if not webview_process.is_alive():
            start_webview_process()

    def on_exit(icon, item):
        icon.stop()

    start_webview_process()

    image = Image.open('logo/logo.png')
    menu = Menu(MenuItem('Open', on_open), MenuItem('Exit', on_exit))
    icon = Icon('Pystray', image, menu=menu)
    icon.run()

    webview_process.terminate()
