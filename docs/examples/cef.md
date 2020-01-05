# CEF support

To use Chrome Embedded Framework on Windows.

``` python
import webview

# To pass custom settings to CEF, import and update settings dict
from webview.platforms.cef import settings
settings.update({
    'persist_session_cookies': True
})


if __name__ == '__main__':
    webview.create_window('CEF Example', 'https://pywebview.flowrl.com/hello')
    webview.start(gui='cef')
```
