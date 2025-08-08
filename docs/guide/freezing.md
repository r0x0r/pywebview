# Freezing

## Android

pywebview is designed to be built with [buildozer](https://buildozer.readthedocs.io/en/latest/). You need to include following lines in your `buildozer.spec` to bundle pywebview correctly

``` ini
requirements = python3,kivy,pywebview
android.add_jars = <path_to_pywebview-android.jar>
```

`pywebview-android.jar` is shipped with `pywebview` and can be found under `site-packages/pywebview/lib`. To get its full path type

``` python
from webview import util
print(util.android_jar_path())
```

You can see a sample `bulldozer.spec` [here](https://github.com/r0x0r/pywebview/blob/a2b8d0449b206db75f9f364639b85db6eac7f07e/examples/todos/buildozer.spec)

## macOS

Use [py2app](https://py2app.readthedocs.io/en/latest/). For a reference setup.py for py2app, look [here](https://github.com/r0x0r/pywebview/blob/master/examples/py2app_setup.py).

## Windows / Linux

Use [pyinstaller](https://www.pyinstaller.org/). Pyinstaller picks all the dependencies found in `pywebview`, even if you don't use them. So for example if you have `PyQt` installed, but use `EdgeChromium` renderer on Windows, pyinstaller will bundle `PyQT` all the same. To prevent that you might want to add unwanted dependencies to `excludes` in your spec file.

Basic pyinstaller script to package an application which uses index.html as content

``` shell
pyinstaller main.py --add-data index.html:.
```

For one file build

``` shell
pyinstaller main.py --add-data index.html:. --onefile
```

>[!warning]
>In Linux if you get a `cannot find python3.xx.so error` you must add it to the pyinstaller binary list for the application to work (replace 'x' with python version)
>``` shell
>pyinstaller main.py --add-data index.html:. --add-binary /usr/lib/x86_64-linux-gnu/libpython3.x.so:. --onefile
>```

In case of using a Javascript library like vue or react you can build the project and use the build directory to the pyinstaller `--add-data`.
>[!warning]
>While using *vite* change the build directory to something else to not conflict with pyinstller's build directory which is also `./dist`

Here is a script to build a vue/react app with pyinstaller (assuming output is your new build directory)

``` shell
pyinstaller main.py --add-data output:.
```

Onefile

``` shell
pyinstaller main.py --add-data output:. --onefile
```

[nuitka](http://nuitka.net/) can be used for freezing as well. You may want to use `--nofollow-import-to` to exclude unwanted dependencies.
