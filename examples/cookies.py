import webview


"""
This example demonstrates how to use cookies and local storage
"""


if __name__ == '__main__':
    window = webview.create_window('Cookie example', 'assets/cookies.html')
    webview.start(debug=True, incognito=False)