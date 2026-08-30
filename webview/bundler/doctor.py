"""
Environment checks for the pywebview2 CLI: which backend/tools are available.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def _has_executable(name: str) -> bool:
    return shutil.which(name) is not None


def check_python() -> CheckResult:
    version = sys.version.split()[0]
    ok = sys.version_info >= (3, 8)
    return CheckResult('Python', ok, version)


def check_pywebview2_backend() -> CheckResult:
    # `webview/__init__.py` reassigns the package-level `guilib` name to a
    # runtime state variable, shadowing the `webview.guilib` submodule
    # attribute -- so the submodule must be pulled from sys.modules rather
    # than accessed as `webview.guilib` after `import webview`.
    try:
        import importlib

        guilib_module = sys.modules.get('webview.guilib') or importlib.import_module(
            'webview.guilib'
        )
        backend = guilib_module.initialize()
        return CheckResult('pywebview2 backend', True, backend.renderer)
    except Exception as e:
        return CheckResult('pywebview2 backend', False, str(e))


def check_pyinstaller() -> CheckResult:
    try:
        import PyInstaller  # noqa: F401

        return CheckResult('PyInstaller', True, PyInstaller.__version__)
    except ImportError:
        return CheckResult('PyInstaller', False, 'not installed (pip install pyinstaller)')


def check_windows_tools() -> list[CheckResult]:
    return [
        CheckResult(
            'WiX (candle/light)',
            _has_executable('candle') or _has_executable('wix'),
            'required for .msi',
        ),
        CheckResult('NSIS (makensis)', _has_executable('makensis'), 'required for .exe installer'),
    ]


def check_macos_tools() -> list[CheckResult]:
    return [
        CheckResult('hdiutil', _has_executable('hdiutil'), 'required for .dmg (ships with macOS)'),
        CheckResult(
            'xcodebuild', _has_executable('xcodebuild'), 'required for iOS and macOS native builds'
        ),
        CheckResult(
            'xcrun', _has_executable('xcrun'), 'required for iOS SDK and simulator tooling'
        ),
    ]


def check_linux_tools() -> list[CheckResult]:
    webkitgtk_ok = False
    try:
        result = subprocess.run(
            ['pkg-config', '--exists', 'webkit2gtk-4.1'], capture_output=True, timeout=5
        )
        webkitgtk_ok = result.returncode == 0
        if not webkitgtk_ok:
            result = subprocess.run(
                ['pkg-config', '--exists', 'webkit2gtk-4.0'], capture_output=True, timeout=5
            )
            webkitgtk_ok = result.returncode == 0
    except (FileNotFoundError, subprocess.SubprocessError):
        pass

    return [
        CheckResult('WebKitGTK', webkitgtk_ok, 'system package, cannot be bundled'),
        CheckResult('dpkg-deb', _has_executable('dpkg-deb'), 'required for .deb'),
        CheckResult('appimagetool', _has_executable('appimagetool'), 'required for AppImage'),
    ]


def check_android_tools() -> list[CheckResult]:
    sdk_home = os.environ.get('ANDROID_HOME') or os.environ.get('ANDROID_SDK_ROOT')
    return [
        CheckResult('buildozer', _has_executable('buildozer'), 'required for Android builds'),
        CheckResult(
            'Android SDK',
            bool(sdk_home and os.path.isdir(sdk_home)),
            sdk_home or 'set ANDROID_HOME or ANDROID_SDK_ROOT',
        ),
        CheckResult(
            'Java (javac)', _has_executable('javac'), 'required by the Android SDK build tools'
        ),
    ]


def run_all(targets: tuple[str, ...] | list[str] | None = None) -> list[CheckResult]:
    results = [check_python(), check_pywebview2_backend(), check_pyinstaller()]

    system = platform.system()
    selected = set(targets or ())
    check_all = not selected
    if system == 'Windows' and (check_all or selected & {'msi', 'nsis'}):
        results += check_windows_tools()
    elif system == 'Darwin' and (check_all or selected & {'dmg', 'ios'}):
        results += check_macos_tools()
    elif system == 'Linux' and (check_all or selected & {'deb', 'appimage'}):
        results += check_linux_tools()

    if check_all or 'android' in selected:
        results += check_android_tools()
    return results
