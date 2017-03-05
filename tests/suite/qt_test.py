import webview
import threading

"""
This example demonstrates how to create a pywebview windows using QT (normally GTK is preferred)
"""

if __name__ == '__main__':
    webview.config["USE_QT"] = True
    webview.create_window("Simple browser", "http://flowrl.com")

