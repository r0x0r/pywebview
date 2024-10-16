"""Set window icon using `webview.start(icon=<file_path>). This is supported only on GTK and QT. For other
platforms, icon is set during freezing."""

import webview

if __name__ == '__main__':
    window = webview.create_window('Set window icon', 'https://pywebview.flowrl.com/hello')
    webview.start(icon='../logo/logo.png')
