# FAQ

## General

### Why does _pywebview_ have to run on the main thread?

The underlying GUI libraries require it. Cocoa has a strict rule that the GUI loop runs on the main thread, and other libraries work best that way. Run your own logic in a function passed to `webview.start(func)`, in a thread, or in a separate process with the `multiprocessing` module.

### `webview` has no attribute `create_window`

You probably have a file named `webview.py` in the current directory. It hides the _pywebview_ package. Rename the file.

### Which renderer is used?

Set the `PYWEBVIEW_LOG=debug` environment variable and run your program. The first lines of the output show the renderer. See [Web engine](/guide/web_engine.md) for the available renderers and how to change them.

## Windows and appearance

### How do I set an application icon?

On Android, set the icon in your bundler. On other platforms, use `webview.start(icon=icon_path)`. On GTK you may need extra steps, depending on the window manager. When you freeze your application, set the icon in the packager as well.

### How do I make a transparent or frameless window?

Use `transparent=True` and `frameless=True` in `create_window`. `transparent` makes the web view transparent, and `frameless` removes the window border. Also use a transparent background in your CSS.

Transparency is not reliable on Windows. It is a known open problem and works on some machines only. See the [API reference](/api/#webview-create-window) for platform support.

### How do I move a frameless window?

By default, you can drag a frameless window from any point (`easy_drag=True`). To drag only from certain elements, add the `pywebview-drag-region` class to them. See [drag area](/api.html#drag-area).

### How do I prevent pinch zoom?

Zooming is off by default. If a page still zooms, check that you did not set `zoomable=True` in `create_window`.

## Links, files and storage

### Links open in my browser instead of the window

Links with `target="_blank"` open in the default browser. To open them in the window, set `webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER'] = False`. Regular links navigate inside the window.

Remember that pages you navigate to do not get the JS API unless you allow their origin. See [Security](/guide/security.md#which-pages-get-the-js-api).

### My local images, styles or scripts do not load

If you use `html=` or `load_html()`, relative paths may not resolve, because there is no server behind the page. Load your files with a relative path in `create_window('index.html')` so that the built-in server serves them, or inline the assets. See [Application architecture](/guide/architecture.md#html-string).

### Cookies and `localStorage` are lost when the application closes

_pywebview_ runs in private mode by default. Start it with `webview.start(private_mode=False)` to keep data. See [Keeping data between runs](/guide/architecture.md#keeping-data-between-runs). On macOS, you cannot change the storage location with `storage_path`.

### How do I read cookies?

Use `window.get_cookies()`. Cookie support differs between platforms. To keep cookies between runs, start with `private_mode=False`.

### How do I get the full path of dropped files?

Use `DOMEventHandler` and subscribe to the `drop` event. The path is in `event['dataTransfer']['files'][0]['pywebviewFullPath']`. See the [drag and drop example](/examples/drag_drop.html).

## JS API

### `pywebview.api` is undefined

The page tried to use the API before it was ready. Wait for the `pywebviewready` event. See [JS–Python bridge](/guide/interdomain.md#wait-for-pywebviewready).

## Packaging

### Frozen executable is too big

The packager picks up dependencies that you do not use. For example, if `PyQt` is installed but you use WinForms on Windows, PyInstaller bundles both. Use the `--exclude-module` option to leave modules out. See [Freezing](/guide/freezing.md).

### My frozen application shows a console window

With PyInstaller, build with the `--noconsole` (or `--windowed`) option.

### Files are missing in the frozen application

Add your HTML, CSS and Javascript files to the package. For PyInstaller, use `--add-data`. Load them with relative paths. See [Freezing](/guide/freezing.md).

## Platform notes

### The window is blank on Windows

- Make sure the [WebView2 runtime](/guide/web_engine.md) is installed.
- Make sure the user can write to the storage directory. Pass another directory with `webview.start(storage_path=...)` if needed.
- Run the application with `PYWEBVIEW_LOG=debug` and read the log. See [Debugging](/guide/debugging.md#common-problems).
