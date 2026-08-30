# Embedded Python runtime contract

The iOS host must embed Python; it cannot launch a `python` executable or
load a desktop Python installation. The runtime implementation belongs in the
native host layer and is consumed by `PyWebViewRuntime`.

## Expected app bundle layout

```text
MyApp.app/
  Frameworks/Python.xcframework/       # linked and signed by Xcode
  python/
    lib/python3.x/
      ... standard library ...
      site-packages/
        ... application dependencies ...
    app/
      main.py
      frontend/
```

The exact Python minor version must be selected by the build workflow and used
consistently for the framework, standard library, and dependency staging.

## Bootstrap sequence

The concrete runtime must:

1. configure UTF-8 mode;
2. disable bytecode writes;
3. disable buffered stdio;
4. set `PYTHONHOME` to the bundled `python` directory;
5. add the bundled standard library, `site-packages`, and application path to
   `PYTHONPATH`;
6. initialize the interpreter on the application-managed runtime thread;
7. invoke the configured entry point; and
8. route bridge requests to the Python-side iOS backend.

Python startup runs off the UIKit main thread because `webview.start()` owns a
blocking application loop. The native `pywebview_ios` module must dispatch all
UIKit/WebKit mutations back to the main thread and provide synchronous Python
results only after the corresponding main-thread operation completes.

Python must not write to the app bundle. Writable state should use the app's
Documents, Library, or temporary directories supplied by the native host.

## Build inputs

The GitHub Actions macOS workflow will eventually need to stage:

- a device and simulator `Python.xcframework`;
- the processed Python standard library;
- pure-Python dependencies;
- separately cross-compiled native dependencies; and
- the application entry point and frontend resources.

The current bundler accepts the framework path through
`PYWEBVIEW_IOS_PYTHON_XCFRAMEWORK` and copies it to the staged project as
`Python.xcframework`.

The initial native bootstrap implementation is in
`runtime/PyWebViewPythonRuntime.m`. It is intentionally isolated from the
host target until the Xcode project generator can select the matching Python
minor version and configure the framework header/library search paths.

Pull-request builds should use an unsigned simulator artifact. Device
framework signing and IPA export belong to the release workflow.
