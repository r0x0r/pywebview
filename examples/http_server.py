"""A built-in HTTP server example."""

import webview


if __name__ == '__main__':
    # HTTP server is started automatically for local relative paths
    webview.create_window('My first HTML5 application', 'assets/index.html')

    # Server certificate is self signed so we need to ignore SSL errors
    webview.settings['IGNORE_SSL_ERRORS'] = True
    webview.start(ssl=True)
