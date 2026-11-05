# Freezing

Freezing turns a _pywebview_ application into a self-contained executable or app bundle. This page has a recipe for each supported tool. It covers what has to be bundled, how to keep unused backends out of the build, how to ship the WebView2 runtime on Windows, and how to sign and notarize on macOS.

## What needs to be bundled

Whichever tool you use, the frozen application must contain:

- `webview/js` – Javascript injected into every page. Without it, page loads fail.
- `webview/lib` on Windows – WebView2 assemblies, `WebView2Loader.dll` under `lib/runtimes/<arch>/native` and `pywebview-runtimeconfig.json`, which _pywebview_ needs to load .NET 6+ through pythonnet.
- `pywebview-android.jar` on Android.
- Your own HTML, CSS and JS assets.

The PyInstaller hook and Nuitka's built-in package configuration already take care of `webview/js` and `webview/lib`. You only add your own assets.

### Locating your assets

_pywebview_ resolves relative paths passed to `create_window(url=...)` against the application root. It detects the root for PyInstaller (`sys._MEIPASS`), py2app (`RESOURCEPATH`) and cx_Freeze (the directory of the executable). Otherwise it falls back to the directory of the entry script. If your assets sit next to the entry point in the bundle, a relative path such as `create_window('App', 'index.html')` works unchanged.

If a tool lays files out differently (briefcase, or Nuitka in `--onefile` mode, which unpacks data to a temporary directory), build the path from your module instead:

``` python
import os

import webview

HERE = os.path.dirname(os.path.abspath(__file__))

webview.create_window('App', os.path.join(HERE, 'web', 'index.html'))
webview.start()
```

### Keeping unused backends out

_pywebview_ selects a backend at runtime, so freezing tools see imports of every backend module. If PyQt, PySide or PyGObject happen to be installed in your environment, they get bundled even when you use a different renderer.

The simplest fix is to freeze from a clean virtual environment that contains only the dependencies your target platform needs. If that is not practical, exclude what you do not use:

- PyInstaller: `--exclude-module PyQt5 --exclude-module PyQt6 --exclude-module PySide2 --exclude-module PySide6 --exclude-module qtpy --exclude-module gi --exclude-module cefpython3`
- Nuitka: `--nofollow-import-to=PyQt5 --nofollow-import-to=PySide6 ...` (same list)

Do not exclude the backend you actually use. To make the frozen application always use a particular backend, pass it to `webview.start(gui='qt')` (or `'gtk'`, `'edgechromium'`, ...). The `PYWEBVIEW_GUI` environment variable does the same, but end users will not have it set, so reserve it for development and debugging.

### Frontend frameworks

If you use Vue, React or a similar framework, build the frontend first and bundle the build output. Vite writes to `./dist` by default, which is also PyInstaller's output directory. Set `build.outDir` to something else, such as `output`, so the two do not collide.

## PyInstaller

[PyInstaller](https://pyinstaller.org/) is the recommended tool on Windows and Linux, and it also works on macOS. _pywebview_ ships a PyInstaller hook, registered through the `pyinstaller40` entry point, so no hidden imports need to be declared.

``` shell
pip install pyinstaller
```

### Windows

``` shell
pyinstaller main.py --add-data index.html:. --windowed --name MyApp
```

For a single-file executable, add `--onefile`. One-file builds unpack themselves to a temporary directory on every start, so they start more slowly. They are also flagged by antivirus software more often than one-folder builds.

Notes:

- `--windowed` (`--noconsole`) suppresses the console window.
- PyInstaller versions before 6.0 require `;` instead of `:` as the `--add-data` separator on Windows.
- `--icon app.ico` sets the executable icon. Pass `icon` to `webview.start()` if you also want a window icon.
- If Windows Defender or SmartScreen flags your build, signing it with an Authenticode certificate (`signtool sign /fd sha256 /tr http://timestamp.digicert.com /td sha256 /a dist\MyApp\MyApp.exe`) is the main remedy.

### Linux

``` shell
pyinstaller main.py --add-data index.html:. --name MyApp
```

PyInstaller bundles the Python side of PyGObject or Qt, but not the system GTK/WebKit2 libraries. Those must be installed on the target machine, so list them as dependencies of your distribution package. See [Installation](/guide/installation.md) for package names.

>[!warning]
>If you get a `cannot find libpython3.x.so` error, add the library to the binary list (replace `x` with your Python minor version):
>``` shell
>pyinstaller main.py --add-data index.html:. --add-binary /usr/lib/x86_64-linux-gnu/libpython3.x.so:. --onefile
>```

### macOS

``` shell
pyinstaller main.py --add-data index.html:. --windowed --name MyApp \
  --icon app.icns --osx-bundle-identifier com.example.myapp
```

`--windowed` produces `dist/MyApp.app`. See [Signing and notarization](#signing-and-notarization-macos) below before distributing it.

## Nuitka

[Nuitka](https://nuitka.net/) compiles your application to C. Its standard package configuration knows about _pywebview_: it includes `webview/js` and `webview/lib` and picks the right `WebView2Loader.dll` for the target architecture, so you only add your own files.

``` shell
pip install nuitka
```

Windows:

``` shell
python -m nuitka --standalone --windows-console-mode=disable ^
  --include-data-files=index.html=index.html main.py
```

Linux:

``` shell
python -m nuitka --standalone --include-data-files=index.html=index.html main.py
```

macOS:

``` shell
python -m nuitka --standalone --macos-create-app-bundle \
  --include-data-files=index.html=index.html main.py
```

Notes:

- Use `--include-data-dir=web=web` to bundle a whole directory of assets.
- Add `--onefile` for a single executable. The same start-up trade-off as with PyInstaller applies.
- Use `--nofollow-import-to` to exclude unused backends (see [above](#keeping-unused-backends-out)).

## py2app (macOS)

[py2app](https://py2app.readthedocs.io/) builds a native `.app` bundle. See the [reference setup.py](https://github.com/r0x0r/pywebview/blob/master/examples/py2app_setup.py).

``` shell
pip install py2app
python setup.py py2app
```

Notes:

- Keep `'webview'` in `includes` (or move it to `packages`) together with `WebKit` and `Foundation`. These are imported dynamically, so py2app does not find them on its own.
- Keep `argv_emulation` set to `False`, as in the reference script.
- When `webview` ends up inside py2app's `python3xx.zip`, _pywebview_ locates its Javascript files in the unpacked `lib/python3.xx/webview` directory instead. Listing `webview` under `packages` keeps the whole package unzipped and avoids that lookup.
- Use `alias` mode (`python setup.py py2app -A`) for fast iteration during development, then do a full build for distribution.

## Briefcase

[Briefcase](https://briefcase.readthedocs.io/) (part of BeeWare) produces platform-native installers: MSI on Windows, `.dmg` on macOS, and deb/rpm/AppImage/Flatpak on Linux. It runs your code as a package, so build asset paths from your module (see [Locating your assets](#locating-your-assets)).

A minimal `pyproject.toml`:

``` toml
[tool.briefcase]
project_name = "MyApp"
bundle = "com.example"
version = "0.1.0"
license = "MIT"
license-files = ["LICENSE"]

[tool.briefcase.app.myapp]
formal_name = "MyApp"
description = "A pywebview application"
long_description = "A longer description, required for Linux packages."
sources = ["src/myapp"]
requires = ["pywebview"]

[tool.briefcase.app.myapp.linux]
requires = ["pywebview[gtk]"]
# Debian/Ubuntu package names. The list may be incomplete for your distribution,
# see the Installation guide
system_requires = ["libgirepository1.0-dev", "libcairo2-dev", "pkg-config"]
system_runtime_requires = ["gir1.2-gtk-3.0", "gir1.2-webkit2-4.1", "libgirepository-1.0-1"]
```

The project layout:

```
pyproject.toml
LICENSE           # required, referenced by license-files
CHANGELOG         # required for Linux packages (CHANGELOG.md also works)
src/myapp/
  __init__.py
  __main__.py     # entry point: create windows and call webview.start()
  web/index.html  # Briefcase copies everything under sources
```

Then:

``` shell
briefcase create
briefcase build
briefcase package
```

On Linux, run Briefcase from a virtual environment created with the distribution's own `python3`. It refuses to build with a separately installed Python. On macOS, `briefcase package` also signs and notarizes the app when it is given a Developer ID identity.

## Shipping the WebView2 runtime (Windows)

The EdgeChromium renderer needs the Microsoft Edge WebView2 Runtime, and your application cannot display content without it. There are two ways to make sure the runtime is present.

### Evergreen runtime (recommended)

The Evergreen runtime is shared by all applications on the machine and updates itself. It comes preinstalled on Windows 11 and on up-to-date Windows 10, but not necessarily on older or locked-down machines.

Download the [Evergreen Bootstrapper](https://developer.microsoft.com/microsoft-edge/webview2/) (`MicrosoftEdgeWebview2Setup.exe`, about 2 MB) and run it from your installer if the runtime is not installed. For example, with Inno Setup:

``` ini
[Files]
Source: "MicrosoftEdgeWebview2Setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Run]
Filename: "{tmp}\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "Installing WebView2 Runtime..."; Check: not IsWebView2Installed

[Code]
function IsWebView2Installed: Boolean;
var
  Version: String;
begin
  // HKLM32 reads the 32-bit registry view, where the per-machine runtime registers itself
  Result :=
    RegQueryStringValue(HKLM32, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version) or
    RegQueryStringValue(HKCU, 'Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version);
  Result := Result and (Version <> '') and (Version <> '0.0.0.0');
end;
```

These are the registry keys of the stable Evergreen runtime. _pywebview_ checks the same keys at start-up, and also accepts the Beta, Dev and Canary channels. Microsoft also offers a standalone Evergreen installer for offline installs.

### Fixed Version runtime

A Fixed Version runtime is a specific WebView2 build that you ship inside your application. It never updates itself, so you are responsible for shipping security updates. It adds roughly 150–200 MB to the download, but it works offline and does not depend on what is installed on the machine.

1. Download the Fixed Version `.cab` for your target architecture from the [WebView2 download page](https://developer.microsoft.com/microsoft-edge/webview2/) and extract it:

   ``` shell
   mkdir webview2
   expand Microsoft.WebView2.FixedVersionRuntime.<version>.x64.cab -F:* webview2
   ```

2. Point _pywebview_ at it before calling `webview.start()`. Relative paths are resolved against the application root, so the same path works in development and in a frozen build:

   ``` python
   webview.settings['WEBVIEW2_RUNTIME_PATH'] = 'webview2/Microsoft.WebView2.FixedVersionRuntime.<version>.x64'
   ```

3. Bundle the directory:

   ``` shell
   pyinstaller main.py --add-data index.html:. --add-data webview2:webview2 --windowed
   ```

   With Nuitka, use `--include-data-dir=webview2=webview2`.

If the configured path does not exist, _pywebview_ logs a warning and tries the system runtime instead. If that is not installed either, the window cannot load, so make sure the path is correct in the frozen build.

### .NET

The WinForms backend loads .NET through pythonnet. It prefers .NET 6 or newer (CoreCLR) and falls back to .NET Framework 4.6.2+. If .NET 6+ is not installed, the .NET Framework that ships with Windows 10 and 11 is used, so no extra installation is normally needed on x64. pythonnet cannot load .NET Framework from native ARM64 Python, so on Windows on ARM64 install the [.NET Desktop Runtime](https://dotnet.microsoft.com/download) 6 or newer there, or ship it with your installer. Set `PYTHONNET_RUNTIME=netfx` or `PYTHONNET_RUNTIME=coreclr` to force one of them.

## Signing and notarization (macOS)

Since macOS Catalina, Gatekeeper blocks apps downloaded from the internet unless they are signed with a Developer ID certificate and notarized by Apple. You need a paid Apple Developer account.

1. Create an entitlements file, `entitlements.plist`. The Python interpreter needs these under the hardened runtime:

   ``` xml
   <?xml version="1.0" encoding="UTF-8"?>
   <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
   <plist version="1.0">
   <dict>
       <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
       <true/>
       <key>com.apple.security.cs.disable-library-validation</key>
       <true/>
   </dict>
   </plist>
   ```

2. Sign the bundle with the hardened runtime. PyInstaller can sign during the build:

   ``` shell
   pyinstaller main.py --add-data index.html:. --windowed --name MyApp \
     --codesign-identity "Developer ID Application: Your Name (TEAMID)" \
     --osx-entitlements-file entitlements.plist
   ```

   For py2app, Nuitka or an already built bundle, sign it with `codesign`. Sign the nested libraries first and the bundle last. Apple discourages `codesign --deep`, because it applies the bundle's entitlements to every nested binary.

   ``` shell
   IDENTITY="Developer ID Application: Your Name (TEAMID)"
   find dist/MyApp.app/Contents -type f \( -name '*.so' -o -name '*.dylib' \) \
     -exec codesign --force --options runtime --timestamp --sign "$IDENTITY" {} \;
   codesign --force --options runtime --timestamp \
     --entitlements entitlements.plist --sign "$IDENTITY" dist/MyApp.app
   codesign --verify --strict --verbose=2 dist/MyApp.app
   ```

3. Notarize and staple the ticket:

   ``` shell
   xcrun notarytool store-credentials notary --apple-id you@example.com --team-id TEAMID
   ditto -c -k --keepParent dist/MyApp.app MyApp.zip
   xcrun notarytool submit MyApp.zip --keychain-profile notary --wait
   xcrun stapler staple dist/MyApp.app
   spctl --assess --type execute --verbose dist/MyApp.app
   ```

   If notarization fails, `xcrun notarytool log <submission-id> --keychain-profile notary` lists the offending files. These are usually unsigned `.so` or `.dylib` files inside the bundle.

If you distribute a `.dmg`, sign and notarize the `.dmg` as well, after stapling the app inside it.

## Android

_pywebview_ is designed to be built with [buildozer](https://buildozer.readthedocs.io/en/latest/). You need to include the following lines in your `buildozer.spec` to bundle _pywebview_ correctly:

``` ini
requirements = python3,kivy,pywebview
android.add_jars = <path_to_pywebview-android.jar>
```

`pywebview-android.jar` is shipped with `pywebview` and can be found under `site-packages/webview/lib`. To get its full path, run:

``` python
from webview import util
print(util.android_jar_path())
```

You can see a sample `buildozer.spec` [here](https://github.com/r0x0r/pywebview/blob/a2b8d0449b206db75f9f364639b85db6eac7f07e/examples/todos/buildozer.spec).
