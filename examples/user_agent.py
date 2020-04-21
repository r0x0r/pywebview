import webview

"""
This example demonstrates how to change the user-agent of a window.
EdgeHTML is not supported.
"""

# To change the user-agent you need to import and update the settings dict from the correct gui
# Change .gtk with your preferred gui
from webview.platforms.gtk import settings
settings.update({
    'user_agent': "Mozilla/5.0 (Linux; U; Android 2.2) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1"
})

if __name__ == '__main__':
    webview.create_window('User Agent Test', 'https://pywebview.flowrl.com/hello')
    # Make sure to change the gui parameter as well
    webview.start(gui='gtk')
