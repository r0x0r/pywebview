import webview

""""
Use SSL with a local HTTP server.
"""

if __name__ == '__main__':
    webview.create_window('Local SSL Test', 'assets/index.html')
    webview.start(ssl=True)
