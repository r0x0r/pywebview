"""Set window icon using `webview.start(icon=<file_path>). Supported on Windows (WinForms), GTK, and QT."""

import webview

if __name__ == '__main__':
    window = webview.create_window('Set window icon', 'https://pywebview.flowrl.com/hello')
    webview.start(icon='../logo/logo.png')
