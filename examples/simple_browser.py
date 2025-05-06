"""The most basic example of creating a webview window."""

import webview

if __name__ == '__main__':
    # Create a standard webview window
    window = webview.create_window('Simple browser', 'https://webglsamples.org/aquarium/aquarium.html')
    webview.start()
