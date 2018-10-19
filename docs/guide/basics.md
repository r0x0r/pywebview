# Installation

If you have the [dependencies](#dependencies) installed, simply:

    pip install pywebview

To automatically fetch and install Python dependencies for your platform, install with the appropriate ["install extras"](http://setuptools.readthedocs.io/en/latest/setuptools.html#declaring-extras-optional-features-with-their-own-dependencies).

(Note that the same code is installed regardless; if more than one of the libraries below are available they will be tried in the order listed in this readme.)

On Windows (using WinForms with `pythonnet`):

    pip install pywebview[winforms]

On Mac (using the Cocoa WebKit widget via `pyobjc`):

    pip install pywebview[cocoa]

On Linux (using GTK3 via `PyGObject`):

    pip install pywebview[gtk3]

On Linux or Mac with either Qt 5:

    pip install pywebview[qt5]  # Qt5 with PyQt5

To use pywebview with PyQt4, you have to install it separately, as it is not available in pypi.

A second implementation for Windows using `pywin32` and `comtypes` is also available:

    pip install pywebview[win32]

# Dependencies

## Windows

On Windows you can choose between Win32 and Windows Forms implementation. The Win32 implementation is not actively developed and misses some features.

For Windows Forms
`pythonnet`

For Win32 you need
`pywin32`, `comtypes`. ActiveState distribution of Python 2 comes with pywin32 preinstalled


## macOS

`pyobjc`. PyObjC comes presintalled with the Python bundled in macOS. For a stand-alone Python installation you have to install it separately. QT is supported as well.


## Linux

For GTK3 based systems:`PyGObject`
On Debian based systems run
`sudo apt-get install python-gi gir1.2-webkit-3.0`

For QT based systems

Either `PyQt5` or `PyQt4`. PyQt4 is deprecated and will be removed in the future.

GTK has a preference over QT, except on KDE systems.


To force a GUI library, use `PYWEBVIEW_GUI` environment variable or set `webview.config.gui` variable. Possible values are `qt`, `gtk` or `win32`.