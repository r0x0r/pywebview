# Change user agent string

Change the user-agent of a window. EdgeHTML is not supported.

``` python
import webview

if __name__ == '__main__':
    webview.create_window('User Agent Test', 'https://pywebview.flowrl.com/hello')
    webview.start(user_agent='Custom user agent')
```