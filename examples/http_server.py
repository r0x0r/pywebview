"""A built-in HTTP server example."""

import webview

if __name__ == '__main__':
    webview.create_window('My first HTML5 application', 'assets/index.html')
    # HTTP server is started automatically for local relative paths
    webview.start(ssl=True)
