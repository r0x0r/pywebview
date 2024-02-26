# Freezing

## Android

pywebview is designed to be built with [buildozer](https://buildozer.readthedocs.io/en/latest/). You need to include following lines in your `buildozer.spec` to bundle pywebview correctly

``` spec
requirements = python3,kivy,pywebview
android.add_jars = <path_to_pywebview-android.jar>
```

You have to include `pywebview-android.jar` with your bundled application. `pywebview-android.jar` is shipped with `pywebview` and can be found under `site-packages/pywebview/lib`. To get `<path_to_pywebview-android.jar>` type

``` python
from webview import util
print(util.android_jar_path())
```

You can see a sample `bulldozer.spec` [here](https://github.com/r0x0r/pywebview/blob/master/examples/todos/bulldozer.spec)

## macOS

Use [py2app](https://py2app.readthedocs.io/en/latest/). For a reference setup.py for py2app, look [here](https://github.com/r0x0r/pywebview/blob/master/examples/py2app_setup.py).

## Windows / Linux

Use [pyinstaller](https://www.pyinstaller.org/). Pyinstaller picks all the dependencies found in `pywebview`, even if you don't use them. So for example if you have `PyQt` installed, but use `EdgeChromium` renderer on Windows, pyinstaller will bundle `PyQT` all the same. To prevent that you might want to add unwanted dependencies to `excludes` in your spec file.
