# Save file dialog

Create a save file dialog after page content is loaded.


``` python
import webview
import time


def save_file_dialog(window):
    time.sleep(5)
    result = window.create_file_dialog(webview.SAVE_DIALOG, directory='/', save_filename='test.file')
    print(result)


if __name__ == '__main__':
    window = webview.create_window('Save file dialog', 'https://pywebview.flowrl.com/hello')
    webview.start(save_file_dialog, window)
```