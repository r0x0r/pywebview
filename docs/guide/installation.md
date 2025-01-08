# Installation

``` bash
pip install pywebview
```

This will install _pywebview_ with default dependencies for each platform.

On Linux you have to explicitly choose between QT and GTK.

``` bash
pip install pywebview[gtk]
```

or

``` bash
# This will install PyQT6
pip install pywebview[qt]
```

Other QT related options are `pywebview[qt5]`, `pywebview[pyside2]` and `pywebview[pyside6]`

Other optional dependencies are `pywebview[android]`, `pywebview[cef]` and `pywebview[ssl]`. CEF is available only for Windows. `ssl` option installs a `cryptography` package, which is needed for using https in local HTTP server.

## Dependencies

### Windows

[pythonnet](https://github.com/pythonnet/pythonnet) (requires > .NET 4.0)

To use with the latest Chromium you need [WebView2 Runtime](https://developer.microsoft.com/en-us/microsoft-edge/webview2/). If you plan to distribute your software, check out [distribution guidelines](https://docs.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution) too.

To use with CEF you need
[cefpython](https://github.com/cztomczak/cefpython/)

QT can be used on Windows as well.

### macOS

[pyobjc](https://pythonhosted.org/pyobjc/)

`PyObjC` comes preinstalled with the Python bundled in macOS. For a stand-alone Python installation you have to install it separately. You do not need the entire `PyObjC` package, these packages suffice

```
pyobjc-core
pyobjc-framework-Cocoa
pyobjc-framework-Quartz
pyobjc-framework-WebKit
pyobjc-framework-security
````

You can also use `QT` on macOS.

### Linux

`pip install pywebview[qt]` should take of QT dependencies. If it does not work or you would like to use GTK, you may try these recipes.

To install QtWebChannel on Debian-based systems (more modern, preferred)

``` bash
sudo apt install python3-pyqt5 python3-pyqt5.qtwebengine python3-pyqt5.qtwebchannel libqt5webkit5-dev
```

To install QtWebKit (legacy, but available for more platforms).

``` bash
sudo apt install python3-pyqt5 python3-pyqt5.qtwebkit python-pyqt5 python-pyqt5.qtwebkit libqt5webkit5-dev
```

[PyGObject](https://pygobject.readthedocs.io/en/latest/) is used with GTK. To install dependencies on Ubuntu, use

``` bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.1
```

For other distributions, consult the [PyGObject documentation](https://pygobject.readthedocs.io/en/latest/getting_started.html)

Note that WebKit2 version 2.22 or greater is required.

::: warning
Starting from Ubuntu Disco Dingo _pywebview_ can be installed via `apt` on Debian based system as `python3-webview` or `python-pywebview`. Ubuntu's distribution lags a few versions behind. If you wish to stay up-to-date, consider installing via `pip`.
:::

### Android

For Android development, refer to Kivy's [packaging instructions for Android](https://kivy.org/doc/stable-1.10.1/guide/packaging-android.html).
