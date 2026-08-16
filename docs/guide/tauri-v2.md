---
prev: /guide/installation
next: /guide/usage
---

# Tauri-inspired workflow

pywebview2 includes an optional project and packaging workflow inspired by
Tauri v2. It provides a project scaffold, a frontend development loop, a
single JSON configuration file, and native packaging through PyInstaller and
platform packaging tools.

This workflow is implemented by the `pywebview2` command. It is separate from
the normal `import webview` API, so existing pywebview applications do not
need to use it.

## Install the CLI

Install pywebview2 with its CLI dependencies:

```bash
pip install "pywebview2[cli]"
```

The CLI dependencies include Click, file watching, Jinja templates, icon
generation, and PyInstaller. Platform-specific installer tools are installed
separately; run `pywebview2 doctor` to see what is available on the current
machine.

## Create a project

Create a vanilla HTML/CSS/JavaScript project:

```bash
pywebview2 init my-app --name "My App" --identifier com.example.myapp --yes
cd my-app
pywebview2 dev
```

The scaffold contains:

```text
my-app/
├── main.py
├── pywebview2.conf.json
└── frontend/
    ├── index.html
    ├── script.js
    └── style.css
```

The `--yes` flag accepts the default values without prompting. The identifier
must use reverse-DNS notation and is used by native packaging.

Vue and React scaffolds are also available:

```bash
pywebview2 init my-vue-app --template vue --name "My Vue App" --yes
pywebview2 init my-react-app --template react --name "My React App" --yes
```

For these templates, install the frontend dependencies before starting the
development command:

```bash
npm --prefix frontend install
pywebview2 dev
```

## Project configuration

`pywebview2.conf.json` is the equivalent of a Tauri `tauri.conf.json` for the
pywebview2 workflow. The scaffold includes a JSON Schema reference for editor
validation.

The important fields are:

| Field | Purpose |
| --- | --- |
| `productName` | Display name and packaged application name |
| `version` | Package version |
| `identifier` | Reverse-DNS application identifier |
| `entry` | Python entry point, normally `main.py` |
| `frontendDist` | Frontend directory loaded outside development mode |
| `frontendDev.command` | Optional command for a frontend dev server |
| `frontendDev.url` | URL loaded while development mode is active |
| `frontendDev.watch` | Frontend paths watched for reloads |
| `window` | Arguments passed to `webview.create_window` |
| `bundle.targets` | Installer formats to produce |
| `bundle.resources` | Files or directories passed to PyInstaller as data |
| `bundle.pyinstaller` | PyInstaller options |
| `bundle.icon` | Source icon basename or platform icon path |
| `mobile.android.buildozerSpecOverrides` | Android Buildozer overrides |

Print the resolved configuration, including defaults, and validate it with:

```bash
pywebview2 config
```

The configuration filename is always `pywebview2.conf.json`.

## Development workflow

Run the application in development mode with:

```bash
pywebview2 dev
```

The command:

1. Starts `frontendDev.command` when both a command and URL are configured.
2. Waits for the frontend URL to become reachable.
3. Runs the Python entry point with `PYWEBVIEW2_DEV=1`.
4. Enables pywebview debug mode and developer tools.
5. Watches Python and configured frontend files.

Frontend changes reload the current webview. Python changes restart the
application. Use `--no-watch` to run the application once:

```bash
pywebview2 dev --no-watch
```

The generated `main.py` uses `frontendDev.url` during development and
`frontendDist/index.html` otherwise. It also installs the reload endpoint only
when `PYWEBVIEW2_DEV=1` is set, and binds that endpoint to localhost with a
per-run token.

For a vanilla project, `frontendDev.command` and `frontendDev.url` are empty,
so changes to local frontend files are reloaded directly. Vue and React
scaffolds use Vite on `http://localhost:5173`.

## Build desktop installers

Set one or more targets in `pywebview2.conf.json`:

```json
{
  "bundle": {
    "targets": ["msi"]
  }
}
```

Then build on the matching host operating system:

```bash
pywebview2 build
```

The build first creates a PyInstaller application in `dist/`, then writes
installers to `dist/installers/`.

| Target | Host OS | Additional tool |
| --- | --- | --- |
| `msi` | Windows | WiX Toolset |
| `nsis` | Windows | NSIS (`makensis`) |
| `dmg` | macOS | `hdiutil` (included with macOS) |
| `deb` | Linux | `dpkg-deb` |
| `appimage` | Linux | `appimagetool` |

Targets can also be supplied without editing the configuration:

```bash
pywebview2 build --target deb
pywebview2 build --target msi --target nsis
```

Useful PyInstaller options include:

```json
{
  "bundle": {
    "icon": "assets/app",
    "resources": ["frontend/**", "assets/**"],
    "pyinstaller": {
      "onefile": true,
      "excludes": ["PyQt5"],
      "extraArgs": []
    }
  }
}
```

The icon command can generate the platform files used by the bundle:

```bash
pywebview2 icon assets/logo.png --output assets/app
```

Packaging is not cross-platform: a Windows installer must be built on
Windows, a DMG on macOS, and Linux packages on Linux. Use this before a build
to identify missing tools:

```bash
pywebview2 doctor
```

## Build Android

Android packaging uses Buildozer and python-for-android rather than
PyInstaller:

```json
{
  "entry": "main.py",
  "bundle": {
    "targets": ["android"]
  }
}
```

Build a debug APK or release APK with:

```bash
pywebview2 build --target android
pywebview2 build --target android --release
```

Android requires Buildozer, the Android SDK/NDK, and Java. The Android entry
point must be named `main.py`. The command generates `buildozer.spec` and
applies `mobile.android.buildozerSpecOverrides` before invoking Buildozer.

The iOS target currently builds the native simulator host through Xcode on a
macOS GitHub Actions runner. Embedded Python runtime packaging and signed
device/IPA export are still separate follow-up work.

## GitHub Actions builds

The repository includes a GitHub Actions smoke-test workflow for the CLI
toolchain: [`cli-build.yml`](https://github.com/imattau/pywebview2/blob/master/.github/workflows/cli-build.yml).
It creates a fresh project with `pywebview2 init`, runs `pywebview2 doctor`,
and builds the platform package using `pywebview2 build`.

The workflow currently builds these targets on their native GitHub-hosted
runners:

| Runner | Target | Artifact |
| --- | --- | --- |
| Ubuntu 22.04 | Android | APK |
| Ubuntu latest | Linux | `.deb` |
| Windows latest | Windows | `.msi` |
| macOS latest | macOS | `.dmg` |

The resulting installers and APKs are uploaded as workflow artifacts. The
workflow can be started from the repository's Actions tab with
`workflow_dispatch`. It also runs for pull requests that change the CLI,
bundler, packaging configuration, or the workflow itself. Its push trigger is
currently limited to the `feature/cli-toolchain` branch.

The repository's broader [`ci.yml`](https://github.com/imattau/pywebview2/blob/master/.github/workflows/ci.yml)
workflow is separate from packaging. It runs code-quality checks and tests
the Ubuntu Qt, Ubuntu GTK, Windows EdgeChromium, and macOS backends. It does
not produce release installers.

## Native application features

The CLI is only one part of the Tauri-inspired workflow. pywebview2 also
provides native integrations that can be used from the Python entry point:

| Feature | API | Use it for |
| --- | --- | --- |
| Persistent settings | `webview.store` | Plain JSON application preferences |
| Secure credentials | `webview.keyring` | Passwords, tokens, and secrets |
| Notifications | `webview.notify` | Native desktop notifications |
| System tray | `webview.tray` | Tray/menu-bar applications |
| Global shortcuts | `webview.shortcuts` | Hotkeys while the app is unfocused |
| Single instance | `webview.enforce_single_instance` | Preventing duplicate app launches |

### Persistent settings

`webview.store` persists JSON-serializable values in the platform application
data directory. It is intentionally unencrypted and is suitable for settings,
not secrets:

```python
import webview

webview.store.set('theme', 'dark')
theme = webview.store.get('theme', default='light')
webview.store.set('window_size', {'width': 1024, 'height': 768})
```

Use `webview.store.Store('/path/to/settings.json')` when an application needs
a separate store. See the [API reference](/api#webviewstore) for `has`,
`delete`, `keys`, and `clear`.

### Secure credentials with keyring

`webview.keyring` uses the native credential mechanism where available:
Keychain on macOS, DPAPI on Windows, and Secret Service on Linux. If Linux
has no reachable Secret Service provider, pywebview2 can use an encrypted-file
fallback when the extra is installed:

```bash
pip install "pywebview2[keyring]"
```

```python
import webview

webview.keyring.set_password('my-app', 'alice', 'secret-value')
token = webview.keyring.get_password('my-app', 'alice')
webview.keyring.delete_password('my-app', 'alice')
```

Keep credentials in the keyring rather than `webview.store`, which is plain
JSON. See the [keyring API](/api#webviewkeyring) for details.

### Native notifications

Display a platform notification from Python:

```python
import webview

webview.notify('Download complete', 'your_file.zip is ready')
```

Notifications use macOS Notification Center, Windows toast/balloon support, or
Linux `libnotify`/`notify-send`. Linux systems may need their notification
backend installed separately.

### System tray and menu-bar icons

Create a tray icon after the native event loop has started. Tray menu actions
reuse pywebview2's `MenuAction` and `MenuSeparator` types:

```python
import webview
from webview.menu import MenuAction, MenuSeparator

window = webview.create_window('My App', 'frontend/index.html')

def show_window():
    window.show()

def quit_app():
    window.destroy()

def on_start():
    webview.tray.create_tray_icon(
        'assets/app.png',
        menu_items=[
            MenuAction('Open', show_window),
            MenuSeparator(),
            MenuAction('Quit', quit_app),
        ],
        tooltip='My App',
    )

webview.start(func=on_start)
```

Tray support is platform-dependent. In particular, Linux uses GTK's
deprecated `Gtk.StatusIcon`, which may not appear on stock GNOME without a
shell extension.

### Global keyboard shortcuts

Register a hotkey that fires even when no pywebview window is focused:

```python
import webview

def show_window():
    window = webview.active_window()
    if window:
        window.show()

webview.shortcuts.register('cmdorctrl+shift+p', show_window)
```

On Linux, global shortcuts require X11 and the optional dependency:

```bash
pip install "pywebview2[shortcuts]"
```

There is no portable Wayland equivalent currently supported. Unregister
shortcuts with `webview.shortcuts.unregister()` or
`webview.shortcuts.unregister_all()` during shutdown.

### Single-instance applications

Call `webview.enforce_single_instance` before creating windows. A second
launch exits after forwarding its arguments to the primary process:

```python
import sys
import webview

def on_second_instance(argv):
    window = webview.active_window()
    if window:
        window.restore()
        window.show()

if not webview.enforce_single_instance(
    on_second_instance=on_second_instance,
    identifier='com.example.myapp',
):
    sys.exit(0)

webview.create_window('My App', 'frontend/index.html')
webview.start()
```

These integrations are available to both manually created applications and
projects generated by `pywebview2 init`. The complete signatures and
platform-specific behavior are documented in the [API reference](/api).

## Tauri-inspired comparison and current limits

The workflow provides the project-level parts of the Tauri model:

| Tauri concept | pywebview2 equivalent |
| --- | --- |
| `create-tauri-app` | `pywebview2 init` |
| `tauri dev` | `pywebview2 dev` |
| `tauri build` | `pywebview2 build` |
| `tauri.conf.json` | `pywebview2.conf.json` |
| Tauri bundler | PyInstaller plus native packaging tools |
| Tauri doctor-style checks | `pywebview2 doctor` |

It is not a drop-in Tauri compatibility layer. Tauri plugins, Rust commands,
Tauri capabilities, permissions, updater support, and cross-platform
cross-compilation are not provided by this workflow.

The configuration schema currently exposes Windows WebView2 runtime options
and macOS signing fields, but installer-specific runtime provisioning and code
signing still depend on the platform toolchain and are not fully automated by
the CLI.

## Troubleshooting

If the CLI cannot find a project configuration, run it from the project
directory or provide the file explicitly:

```bash
pywebview2 dev --config path/to/pywebview2.conf.json
pywebview2 build --config path/to/pywebview2.conf.json
```

If frontend file watching is unavailable, reinstall the CLI extra:

```bash
pip install -U "pywebview2[cli]"
```

If packaging fails, run `pywebview2 doctor` and install the missing native
tool required by the selected target.
