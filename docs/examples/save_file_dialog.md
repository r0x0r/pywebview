# Save file dialog

Create a save file dialog after page content is loaded.


``` python
import webview
import threading


def save_file_dialog():
    import time
    time.sleep(5)
    print(webview.create_file_dialog(webview.SAVE_DIALOG,
                                     directory="/",
                                     save_filename='test.file'))


if __name__ == '__main__':
    t = threading.Thread(target=save_file_dialog)
    t.start()

    webview.create_window("Save file dialog", "http://pywebview.flowrl.com")
```