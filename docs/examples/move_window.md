# Move window

Set window coordinates and move window after its creation.


``` python
import webview
from time import sleep

def move(window):
    sleep(2)
    window.move(0, 0)


if __name__ == '__main__':
    window = webview.create_window('Move window example', html='<h1>Move window</h1>', x=100, y=200)
    webview.start(move, window)
```
