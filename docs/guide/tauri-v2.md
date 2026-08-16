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

There is currently no iOS target.

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
