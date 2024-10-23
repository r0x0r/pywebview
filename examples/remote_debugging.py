import webview

"""
Enable remote debugging when using `edgechromium`.
This can be used to write tests for the application using Playwright.
See [https://playwright.dev/docs/webview2](https://playwright.dev/docs/webview2) for how to configure it.
"""

if __name__ == '__main__':
    webview.settings['REMOTE_DEBUGGING_PORT'] = 9222

    window = webview.create_window('Webview', 'https://pywebview.flowrl.com/hello')
    webview.start()
