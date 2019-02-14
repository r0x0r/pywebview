# Installation

``` bash
pip install pywebview
```

This will install _pywebview_ with default dependencies. To install _pywebview_ with PyQt5 (available on Linux and macOS) use

``` bash
pip install pywebview[qt]
```

To install _pywebview_ with CEF (available on Windows) use

``` bash
pip install pywebview[cef]
```


## Dependencies

### Windows

[pythonnet](https://github.com/pythonnet/pythonnet)

`pythonnet` requires to have .NET 4.0 installed

[cefpython](https://github.com/cztomczak/cefpython/)

``` bash
pip install cefpython3
```

### macOS

[pyobjc](https://pythonhosted.org/pyobjc/)

`PyObjC` comes presintalled with the Python bundled in macOS. For a stand-alone Python installation you have to install it separately. 
You can also use QT5 in macOS

### Linux

You have to install Linux dependencies manually. You can choose between GTK and QT.

[PyGObject](https://pygobject.readthedocs.io/en/latest/) is used with GTK. To install dependencies on Ubuntu for both Python 3 and 2

``` bash
sudo apt install python-gi python-gi-cairo python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.0
```

For other distributions, consult the [PyGObject documentation](https://pygobject.readthedocs.io/en/latest/getting_started.html)

<br/><br/>

[PyQt5](http://pyqt.sourceforge.net/Docs/PyQt5/index.html) is used with QT. `pywebview` supports both QtWebChannel (newer and preferred) and QtWebKit implementations. Use QtWebChannel, unless it is not available on your system.

To install QtWebChannel on Debian-based systems.

``` bash
sudo apt install python3-pyqt5 python3-pyqt5.qtwebengine python3-pyqt5.qtwebchannel python-pyqt5 python-pyqt5.qtwebengine python-pyqt5.qtwebchannel libqt5webkit5-dev 
```

To install QtWebKit.

``` bash
sudo apt install python3-pyqt5 python3-pyqt5.qtwebkit python-pyqt5 python-pyqt5.qtwebkit libqt5webkit5-dev 
```
