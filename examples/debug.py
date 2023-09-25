"""
A debug window example that opens DevTools.
"""

import webview

if __name__ == '__main__':
    webview.create_window('Debug window', 'https://pywebview.flowrl.com/hello')
    webview.start(debug=True)
