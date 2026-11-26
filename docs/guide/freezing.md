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

## Opening files

To let users open documents with your application, e.g. by double-clicking a file in a file manager, register the file types with the operating system. The opened files are delivered with [webview.events.opened](/api/#webview-events-opened), which also delivers URLs of custom URL schemes registered by the application, e.g. `myapp://item/1`. Subscribe to the event before calling `webview.start()`, so that files opened at launch are not missed.

### macOS

Declare the file types in `CFBundleDocumentTypes` in the `plist` option of your py2app `setup.py`, or in `info_plist` of a PyInstaller `BUNDLE`. Each file type is a dictionary inside the `CFBundleDocumentTypes` list.

``` python
OPTIONS = {
    'plist': {
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': 'My document',
                'CFBundleTypeRole': 'Editor',
                'CFBundleTypeExtensions': ['mydoc'],
            },
        ],
    },
}
```

URL schemes are declared in `CFBundleURLTypes`, e.g. `{'CFBundleURLName': 'com.example.myapp', 'CFBundleURLSchemes': ['myapp']}`. macOS sends opened files and URLs to the running application, so the event is fired both at launch and while the application is running. `argv_emulation` is not needed. The file types are registered when the application is first launched or copied to a folder such as `/Applications`. Applications in temporary folders are not registered.

### Windows and Linux

The operating system starts the application with the file paths or URLs as command line arguments. The event is fired once at startup with the arguments that are existing files or URLs. Opening another file while the application is running starts a second instance of the application. To open it in the running instance instead, pass `single_instance=True` to `webview.start()`. The second instance then hands its command line to the running instance and exits.

On Windows, file types are registered in the registry, usually by the installer of your application:

```
HKEY_CURRENT_USER\Software\Classes\.mydoc            (Default) = MyApp.Document
HKEY_CURRENT_USER\Software\Classes\MyApp.Document\shell\open\command
                                                     (Default) = "C:\Path\To\MyApp.exe" "%1"
```

A URL scheme is registered the same way, under a key named after the scheme:

```
HKEY_CURRENT_USER\Software\Classes\myapp             (Default) = URL:MyApp
                                                     URL Protocol = ""
HKEY_CURRENT_USER\Software\Classes\myapp\shell\open\command
                                                     (Default) = "C:\Path\To\MyApp.exe" "%1"
```

On Linux, list the MIME types in the `.desktop` file of your application and pass the files with `%F`. A URL scheme is listed as `x-scheme-handler/myapp`. To receive both files and URLs, pass them with `%U` instead; files then arrive as `file://` URLs, which are delivered as paths. A new file type also needs a [shared MIME info](https://specifications.freedesktop.org/shared-mime-info-spec/latest/) definition.

``` ini
[Desktop Entry]
Type=Application
Name=MyApp
Exec=myapp %F
MimeType=application/x-mydoc;
```

### Android

Add an intent filter for the `VIEW` action to the activity, and use the `singleTask` launch mode, so that documents opened while the application is running are sent to it instead of to a new activity. In `buildozer.spec`:

``` ini
android.manifest.intent_filters = intent_filters.xml
android.manifest.launch_mode = singleTask
```

``` xml
<intent-filter>
    <action android:name="android.intent.action.VIEW" />
    <category android:name="android.intent.category.DEFAULT" />
    <data android:scheme="content" />
    <data android:mimeType="text/plain" />
</intent-filter>
```

Android gives the application access to the document rather than a path, so _pywebview_ copies the document to the cache directory of the application and passes the path of the copy. Changes to the copy are not written back to the original document.
