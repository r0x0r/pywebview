# Quit confirmation dialog

``` python
import webview

if __name__ == '__main__':
    # Create a standard webview window
    webview.create_window('Confirm Quit Example',
                          'http://pywebview.flowrl.com',
                          confirm_quit=True)
```