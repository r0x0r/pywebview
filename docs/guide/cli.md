# CLI toolchain

pywebview2 ships an optional CLI, inspired by Tauri's `init`/`dev`/`build` workflow, that scaffolds a project and turns it into native installers. Install it with:

``` bash
pip install "pywebview2[cli]"
```

This is the recommended path for new projects. For advanced or fully custom freezing setups, see [Freezing](freezing.md), which the CLI's `build` command builds on top of.

## `pywebview init`

Scaffolds a new project:

``` bash
pywebview2 init my-app --name "My App" --identifier com.example.myapp --yes
```

This creates `pywebview2.conf.json`, `main.py`, and a `frontend/` directory with a minimal HTML/CSS/JS starting point.

## `pywebview.conf.json`

Project configuration, analogous to `tauri.conf.json`. Key fields:

- `entry` — Python entry point that calls `webview.start()`
- `window` — passthrough of `webview.create_window()` kwargs
- `bundle.targets` — installer formats to build: `msi`, `nsis`, `dmg`, `deb`, `appimage`
- `bundle.pyinstaller` — PyInstaller passthrough (`onefile`, `excludes`, `extraArgs`)
- `bundle.windows.webview2InstallMode` — how the WebView2 runtime is provisioned
- `bundle.linux.debDepends` — native package dependencies declared in the generated `.deb`
- `frontendBuild.command` — optional command run before desktop packaging, such as `npm --prefix frontend run build`

Run `pywebview2 config` to print the fully resolved configuration (defaults merged with your file) and validate it.

## `pywebview2 dev`

Runs the app with `PYWEBVIEW2_DEV=1` set and debug/devtools enabled. Frontend changes reload the current webview; Python changes restart the app. Use `pywebview2 dev --no-watch` to run once.

## `pywebview2 build`

Runs `frontendBuild.command` when configured, freezes the app with PyInstaller (reusing the `webview.__pyinstaller` hook automatically), then builds any installer formats listed in `bundle.targets` for the current OS. The command exits unsuccessfully if a requested target cannot be built.

| Target | Platform | External tool required |
|---|---|---|
| `msi` | Windows | [WiX Toolset](https://wixtoolset.org/) |
| `nsis` | Windows | [NSIS](https://nsis.sourceforge.io/) |
| `dmg` | macOS | `hdiutil` (built in) |
| `deb` | Linux | `dpkg-deb` |
| `appimage` | Linux | [appimagetool](https://github.com/AppImage/appimagetool) |
| `android` | Linux | [buildozer](https://buildozer.readthedocs.io/) + Android SDK/NDK/Java |

`build` only attempts targets that are buildable on the host OS -- there is no cross-compilation for installers (e.g. a `.dmg` requires building on macOS). Run `pywebview2 doctor --target deb` to check a selected target's prerequisites.

WebKitGTK (Linux) cannot be bundled; `.deb` declares it via `Depends:` and AppImage builds print a warning that it must already be present on the target system. WebView2 (Windows) is provisioned per `bundle.windows.webview2InstallMode`.

`android` skips the PyInstaller freeze step (buildozer/python-for-android does its own build) and instead templates a `buildozer.spec` from `mobile.android.buildozerSpecOverrides` and runs `buildozer android debug` (or `--release` for a release build). The entry point must be named `main.py`, which buildozer requires. This wraps the existing manual buildozer workflow described in [Freezing](freezing.md#android) -- pywebview's Android backend itself (Kivy/pyjnius-based) is unchanged.

## `pywebview2 icon`

Generates a `.ico`, `.icns`, and a set of PNGs from a single source image:

``` bash
pywebview2 icon logo.png --output icons
```

## `pywebview2 doctor`

Checks the local environment: Python version, which pywebview2 backend is importable, and which external packaging tools are on `PATH`. Pass `--target` to check only the prerequisites relevant to a build, for example `pywebview2 doctor --target android`.

For the full Tauri-inspired workflow, including Vue/React templates, Android, iOS, and GitHub Actions, see [Tauri-inspired workflow](tauri-v2.md).
