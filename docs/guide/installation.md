# Installation

``` bash
pip install pywebview
```

This will install _pywebview_ with default dependencies.


## Dependencies

### Windows

[pythonnet](https://github.com/pythonnet/pythonnet)

`pythonnet` requires to have .NET 4.0 installed


### macOS

[pyobjc](https://pythonhosted.org/pyobjc/)

`PyObjC` comes presintalled with the Python bundled in macOS. For a stand-alone Python installation you have to install it separately. 
You can also use QT5 in macOS

### Linux

If you are running KDE, QT will be chosen, otherwise GTK is the default. Additionally for both GTK and QT you have to install WebKit separately. 

[PyGObject](https://pygobject.readthedocs.io/en/latest/) library is used with GTK. To install dependencies on Ubuntu 

**Python 3**
``` bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.0
```

**Python 2**
``` bash
sudo apt install python-gi python-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.0
```
<br/><br/>

[PyQt5](http://pyqt.sourceforge.net/Docs/PyQt5/index.html) is used with QT. On Ubuntu you need following packages

**Python 3**
``` bash
sudo apt install python3-pyqt5 python3-pyqt5.qtwebkit libqt5webkit5-dev 
```

**Python 2**
``` bash
sudo apt install python-pyqt5 python-pyqt5.qtwebkit libqt5webkit5-dev 
```
