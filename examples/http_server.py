"""A built-in HTTP server example."""

import webview

if __name__ == '__main__':
    webview.create_window('My first HTML5 application', 'assets/index.html', text_select=True)
    # HTTP server is automatically started for local relative paths
    webview.start()
