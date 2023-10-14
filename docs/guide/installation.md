# Installation

``` bash
pip install pywebview
```

This will install _pywebview_ with default dependencies. To install _pywebview_ with PySide2 (available on Linux and macOS and Windows) use

``` bash
pip install pywebview[qt]
```

To install _pywebview_ with CEF (available on Windows) use

``` bash
pip install pywebview[cef]
```


## Dependencies

### Windows

[pythonnet](https://github.com/pythonnet/pythonnet) (requires > .NET 4.0)

To use with the latest Chromium you need [WebView2 Runtime](https://developer.microsoft.com/en-us/microsoft-edge/webview2/). If you plan to distribute your software, check out [distribution guidelines](https://docs.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution) too.

To use with CEF you need
[cefpython](https://github.com/cztomczak/cefpython/)

``` bash
pip install cefpython3
```


### macOS

[pyobjc](https://pythonhosted.org/pyobjc/)

`PyObjC` comes presintalled with the Python bundled in macOS. For a stand-alone Python installation you have to install it separately.
You can also use QT5 in macOS

### Linux


`pip install pywebview[qt]` should take of QT dependencies. If it does not work or you would like to use GTK, you may try these recipes.

[PyGObject](https://pygobject.readthedocs.io/en/latest/) is used with GTK. To install dependencies on Ubuntu for both Python 3 and 2

``` bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.1
```

For other distributions, consult the [PyGObject documentation](https://pygobject.readthedocs.io/en/latest/getting_started.html)


Note that WebKit2 version 2.22 or greater is required for certain features to work correctly. If your distribution ships with an older version, you may need to install it manually from a backport.

<br/><br/>

[PySide2](https://doc.qt.io/qtforpython-5/) is used with QT. `pywebview` supports both QtWebChannel (newer and preferred) and QtWebKit implementations. Use QtWebChannel, unless it is not available on your system.

To install QT via pip
``` bash
pip install qtpy pyside2
```

To install QtWebChannel on Debian-based systems (more modern, preferred)

``` bash
sudo apt install python3-pyqt5 python3-pyqt5.qtwebengine python3-pyqt5.qtwebchannel libqt5webkit5-dev
```

To install QtWebKit (legacy, but available for more platforms).

``` bash
sudo apt install python3-pyqt5 python3-pyqt5.qtwebkit python-pyqt5 python-pyqt5.qtwebkit libqt5webkit5-dev
```

<br/>

::: warning
Starting from Ubuntu Disco Dingo _pywebview_ can be installed via `apt` on Debian based system as `python-pywebview`. This package features an old version of _pywebview_ that is API incompatible with the current version. If you choose to install it, you can find documentation [here](/2.4)
:::
