# Freezing

To freeze your application use [py2app](https://py2app.readthedocs.io/en/latest/) on macOS and [pyinstaller](https://www.pyinstaller.org/) on Windows. For a reference setup.py for py2app, look [here](https://github.com/r0x0r/pywebview/blob/master/examples/py2app_setup.py)

For Pyinstaller you need to include either [WebBrowserInterop.x86.dll](https://github.com/r0x0r/pywebview/blob/master/webview/lib/WebBrowserInterop.x86.dll) or [WebBrowserInterop.x64.dll](https://github.com/r0x0r/pywebview/blob/master/webview/lib/WebBrowserInterop.x64.dll) depending on whether you build against 32-bit or 64-bit Python. The DLLs bundled with _pywebview_ and are located in the `site-packages/webview/lib` directory. There is currently an effort to provide a hook for pyinstaller that would bundle this DLL automatically, but for now you have to resort to this step.


_TODO: add Linux freezing guide_


