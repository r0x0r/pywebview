# Multi-window

Create multiple windows.


``` python
import webview


def third_window():
    # Create a new window after the loop started
    third_window = webview.create_window('Window #3', html='<h1>Third Window</h1>')


if __name__ == '__main__':
    # Master window
    master_window = webview.create_window('Window #1', html='<h1>First window</h1>')
    child_window = webview.create_window('Window #2', html='<h1>Second window</h1>')
    webview.start(third_window)

```