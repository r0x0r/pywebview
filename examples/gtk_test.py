import os
os.environ["USE_GTK"] = "true"

import webview

"""
This example creates a webview window using GTK (normally QT is preferred)
"""

if __name__ == '__main__':
    webview.create_window("GTK browser", "http://www.flowrl.com")

