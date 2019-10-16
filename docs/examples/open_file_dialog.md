# Open file dialog

Create an open file dialog after page content is loaded.


``` python
import webview


def open_file_dialog(window):
    file_types = ('Image Files (*.bmp;*.jpg;*.gif)', 'All files (*.*)')

    result = window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=True, file_types=file_types)
    print(result)


if __name__ == '__main__':
    window = webview.create_window('Open file dialog example', 'https://pywebview.flowrl.com/hello')
    webview.start(open_file_dialog, window)
```