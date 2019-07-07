# Minimum window size

Set minimum window dimensions.

``` python
import webview


if __name__ == '__main__':
    # Create a resizable webview window with minimum size constraints
    webview.create_window('Minimum window size',
                          'https://pywebview.flowrl.com/hello',
                          min_size=(400, 200))
    webview.start()
```
