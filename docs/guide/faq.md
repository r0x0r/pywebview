# Troubleshooting

## webview has no attribute create_window

You probably have a file named `webview.py` in the current directory. Renaming it to something else should fix the problem.

## Terminal window receives key events on macOS

If you create a virtual environment using the built-in Python on macOS, a pywebview window will have issues with keyboard focus and Cmd+Tab. The issue can be avoided by using other Python installation. For example to use Python 3 via [Homebrew](https://brew.sh).

``` bash
brew install python3
virtualenv pywebview_env -p python3
```

## Frozen executable is too big

Big executable size is caused by packager picking up unnecessary dependencies. For example if you have `PyQt` installed but use Winforms on Windows, Pyinstaller will bundle both frameworks. To avoid this in Pyinstausingller, use `--exclude-module` option to explicitly omit the module.
