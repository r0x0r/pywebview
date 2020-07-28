import webview

"""
This example demonstrates how to create a webview window.
"""

if __name__ == '__main__':
    # Create a standard webview window
    window = webview.create_window('Simple browser', 'https://webkit.org/blog-files/content-security-policy/csp-style-hash.html')
    webview.start()
