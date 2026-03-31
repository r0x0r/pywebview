# FAQ

## How do I set an application icon?

For macOS, Windows, and Android, the application icon is set via a bundler and embedded in the resulting executable. For GTK and QT, you can set the application icon using `webview.start(icon=icon_path)`, but you might need some additional adjustments to get your icon visible depending on the window manager you use.

## Why does _pywebview_ have to run on a main thread?

This is dictated by underlying GUI libraries _pywebview_ is based on. GUI loop is expected to run on a main thread. While some libraries allow the GUI to be run in a sub-thread, Cocoa has a strict requirement regarding the main thread. If you need your logic to run in a main thread, use the `multiprocessing` module.

## webview has no attribute create_window

You probably have a file named `webview.py` in the current directory. Renaming it to something else should fix the problem.

## What renderer is used?

Set `PYWEBVIEW_LOG=debug` environment variable before running your programme. It will display used renderer in the first line of the program output. See available renderers [here](/guide/renderer)

## Terminal window receives key events on macOS

If you create a virtual environment using the built-in Python on macOS, a pywebview window will have issues with keyboard focus and Cmd+Tab. The issue can be avoided by using other Python installation. For example to use Python 3 via [Homebrew](https://brew.sh).

``` bash
brew install python3
virtualenv pywebview_env -p python3
```

## Frozen executable is too big

Big executable size is caused by packager picking up unnecessary dependencies. For example if you have `PyQt` installed but use Winforms on Windows, Pyinstaller will bundle both frameworks. To avoid this in Pyinstaller, use `--exclude-module` option to explicitly omit the module.

## How do I get a full path of dropped files in `drop` event?

Use `DOMEventHandler` and subscribe to the `drop` event. The file path information is stored in `event['dataTransfer']['files'][0]['pywebviewFullPath']` property of the event object. See [this example](/examples/drag_drop.html) for details.
