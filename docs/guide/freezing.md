# Freezing

## macOS

Use [py2app](https://py2app.readthedocs.io/en/latest/). For a reference setup.py for py2app, look [here](https://github.com/r0x0r/pywebview/blob/master/examples/py2app_setup.py).

## Windows

Use [pyinstaller](https://www.pyinstaller.org/).

If you are using *PyInstaller>=3.6*, it should work out of the box as there is hook that takes care of the bundling of necessary dlls. Therefore, this version of PyInstaller is the recommended one.

Should you need to use prior versions of PyInstaller (<=3.5), you will need to bundle the dlls yourself. Either [WebBrowserInterop.x86.dll](https://github.com/r0x0r/pywebview/blob/master/webview/lib/WebBrowserInterop.x86.dll) or [WebBrowserInterop.x64.dll](https://github.com/r0x0r/pywebview/blob/master/webview/lib/WebBrowserInterop.x64.dll) depending on whether you build against 32-bit or 64-bit Python. 
The DLLs bundled with _pywebview_ and are located in the `site-packages/webview/lib` directory. 

## Linux

Use [pyinstaller](https://www.pyinstaller.org/).
