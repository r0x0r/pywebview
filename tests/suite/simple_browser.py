import webview


def run():
    webview.create_window("Simple browser", "http://www.flowrl.com")


def stop():
    webview.destroy_window()