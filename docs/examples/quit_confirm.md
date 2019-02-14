# Quit confirmation dialog

``` python
import webview

if __name__ == '__main__':
    # Create a standard webview window
    webview.create_window('Confirm Quit Example',
                          'https://pywebview.flowrl.com/hello',
                          confirm_quit=True)
```