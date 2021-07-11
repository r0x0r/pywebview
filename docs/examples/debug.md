# Debugging

To open up debugging console, right click on an element and select Inspect.
Note: To be able to open the DevTools through the contextmenu, you have to include two parameters inside the start function to be like this: webview.start(debug=True, gui="cef")
``` python
import webview

if __name__ == '__main__':
    webview.create_window('Debug window', 'https://pywebview.flowrl.com/hello')
    webview.start(debug=True)
```
