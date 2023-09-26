"""
This example demonstrates how to set vibrancy on macOS.
"""

import webview


def load_css(window):
    window.load_css('body { background: transparent !important; }')


if __name__ == '__main__':
    window = webview.create_window(
        'Vibrancy example', 'https://pywebview.flowrl.com/hello', transparent=True, vibrancy=True
    )
    webview.start(load_css, window)
