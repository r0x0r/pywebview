"""A window with a quit confirmation dialog."""

import webview

if __name__ == '__main__':
    # Create a standard webview window
    webview.create_window(
        'Confirm Quit Example', 'https://pywebview.flowrl.com/hello', confirm_close=True
    )
    webview.start()
