import webview


"""
This example demonstrates how to use a built-in http server to serve local files
"""
if __name__ == '__main__':
    webview.create_window('My first HTML5 application', 'assets/index.html')
    webview.start(http_server=True)
