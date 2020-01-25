# Freezing

## macOS

Use [py2app](https://py2app.readthedocs.io/en/latest/). For a reference setup.py for py2app, look [here](https://github.com/r0x0r/pywebview/blob/master/examples/py2app_setup.py).

## Windows

Use [pyinstaller](https://www.pyinstaller.org/).

You need to include following DLLs in your bundle:
- either [WebBrowserInterop.x86.dll](https://github.com/r0x0r/pywebview/blob/master/webview/lib/WebBrowserInterop.x86.dll) or [WebBrowserInterop.x64.dll](https://github.com/r0x0r/pywebview/blob/master/webview/lib/WebBrowserInterop.x64.dll) depending on whether you build against 32-bit or 64-bit Python.
- `Microsoft.Toolkit.Forms.UI.Controls.WebView.dll` and `Microsoft.Toolkit.Forms.UI.Controls.WebView.LICENSE.md`

There is currently an effort to provide a hook for pyinstaller that would bundle these DLLs automatically, but for now you have to resort to this step.

## Linux

Use [pyinstaller](https://www.pyinstaller.org/).
