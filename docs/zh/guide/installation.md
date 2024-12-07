# 安装

``` bash
pip install pywebview
```

这将安装带有默认依赖项的 _pywebview_ 。如果你想使用PySide2（在Linux、macOS和Windows上可用），请使用

``` bash
pip install pywebview[qt]
```

要在 _pywebview_ 中使用CEF（在Windows上可用），请使用

``` bash
pip install pywebview[cef]
```

## 依赖

### Windows

[pythonnet](https://github.com/pythonnet/pythonnet) (需要 > .NET 4.0)

要使用最新的Chromium，您需要安装[WebView2运行时](https://developer.microsoft.com/en-us/microsoft-edge/webview2/). 如果您计划分发软件，请查看[分发指南](https://docs.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution)。

要使用CEF，您需要
[cefpython](https://github.com/cztomczak/cefpython/)

``` bash
pip install cefpython3
```


### macOS

[pyobjc](https://pythonhosted.org/pyobjc/)

`PyObjC`预装在了了macOS中捆绑的Python。对于独立的Python安装，您必须单独安装`PyObjC`。
您还可以在macOS中使用`PyQt5`或`PyQt6`。

### Linux

`pip install pywebview[qt]` should take of QT dependencies. If it does not work or you would like to use GTK, you may try these recipes.

[PyGObject](https://pygobject.readthedocs.io/en/latest/) is used with GTK. To install dependencies on Ubuntu for both Python 3 and 2

``` bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.1
```

For other distributions, consult the [PyGObject documentation](https://pygobject.readthedocs.io/en/latest/getting_started.html)

Note that WebKit2 version 2.22 or greater is required.

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
Starting from Ubuntu Disco Dingo _pywebview_ can be installed via `apt` on Debian based system as `python3-webview`. Ubuntu's distribution lags a few versions behind (latest is 3.3.5 on mantic). If you wish to stay up-to-date, consider installing via  `pip`.
:::

### Android

For Android development, refer to Kivy's [packaging instructions for Android](https://kivy.org/doc/stable-1.10.1/guide/packaging-android.html).