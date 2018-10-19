# Freezing

Use py2app on OS X and pyinstaller on Windows. For reference setup.py files, look in `examples/py2app_setup.py`. Pyinstaller builds a working executable out of the box, however you need to include .NET assembly Python.Runtime.dll (of pythonnet) to the target directory by providing built-in pyinstaller hook. The proper way to use this clr hook is to specify --hidden-import=clr from command-line or hiddenimports=['clr'] in spec file. This should take care of finding Python.Runtime.DLL hidden import for Windows.





