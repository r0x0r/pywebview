# Stop Freezing Main Thread

Stop Freezing Main Thread

**supported platforms**
- windows(Internet Explorer, Edge, CEF(Chromium Embeded FrameWork))
- Linux(GTK, QT)
- MaxOS(QT)

> **MacOS Cocoa(default) not supported**

**set `block` option of `webview.start` to False**

``` python
import webview

if __name__ == '__main__':
    # Master window
    master_window = webview.create_window('Window #1', html='<h1>First window</h1>')
    child_window = webview.create_window('Window #2', html='<h1>Second window</h1>')
    
    process = webview.start(block = False)
    
    # third window created after gui loop started
    third_window = webview.create_window('Window #3', html='<h1>Third Window</h1>')
    process.join()

```

`process` returned by `webview.start` is [multiprocessing.Process](https://docs.python.org/3/library/multiprocessing.html#multiprocessing.Process) like object
all methods are working.
but properties are experimental

## `Process` object
### `join(timeout=None)`
join GUI event loop to main thread
> Warning: This will freeze main thread.
- timeout(optional) - timeout in seconds(int). default is None. if timeout, kills GUI event loop after timeout.

### `close()`
close all windows and kill GUI event loop.
