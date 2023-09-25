import webview

"""
Create a CEF window with custom Chrome settings. Available only on Windows.
"""

# To pass custom settings to CEF, import and update settings dict
from webview.platforms.cef import browser_settings, settings

settings.update({'persist_session_cookies': True})
browser_settings.update({'dom_paste_disabled': False})

if __name__ == '__main__':
    webview.create_window('CEF browser', 'https://pywebview.flowrl.com/hello')
    webview.start(gui='cef')
