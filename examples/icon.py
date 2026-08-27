"""Set window icon using `webview.start(icon=<file_path>). This is supported on GTK, QT, macOS and Windows.
On Android, icon is set during freezing."""

import webview

if __name__ == '__main__':
    window = webview.create_window('Set window icon', 'https://pywebview.flowrl.com/hello')
    webview.start(icon='../assets/logo.png')
