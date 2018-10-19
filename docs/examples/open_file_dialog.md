# Open file dialog

Create an open file dialog after page content is loaded.


``` python
import webview
import threading


def open_file_dialog():
    file_types = ('Image Files (*.bmp;*.jpg;*.gif)', 'All files (*.*)')

    print(webview.create_file_dialog(webview.OPEN_DIALOG,
                                     allow_multiple=True,
                                     file_types=file_types))


if __name__ == '__main__':
    t = threading.Thread(target=open_file_dialog)
    t.start()

    webview.create_window("Open file dialog example", "http://pywebview.flowrl.com")
```