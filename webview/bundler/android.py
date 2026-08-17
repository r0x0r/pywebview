"""
Android packaging: templates buildozer.spec and shells out to buildozer.

Wraps buildozer the same way freeze.py wraps PyInstaller for desktop -- this
module only generates config and orchestrates the external tool, it never
reimplements python-for-android. pywebview2's existing Android backend
(webview/platforms/android/, python-for-Android/pyjnius-based) and guilib.py's Android
detection are untouched; this only adds packaging orchestration around the
already-documented buildozer workflow (see docs/guide/freezing.md and
examples/todos/buildozer.spec).
"""

from __future__ import annotations

import configparser
import os
import shutil
import subprocess
from typing import Any

# python3 pinned rather than left open: an unpinned python3 recipe resolves
# to the newest CPython p4a supports, and pip's install of pywebview2's pure
# -Python deps for that Android-arch/version wheel tag combination is prone
# to breaking on the newest releases (e.g. "not a supported wheel on this
# platform" for a brand-new cp3xx android_24_arm64_v8a tag). 3.11 is a more
# battle-tested target for python-for-android at the time of writing.
# hostpython3 must be pinned to the same version -- p4a requires the
# build-host interpreter and the on-device target interpreter to match
# ("python3 should have same version as hostpython3") and won't infer it
# from the python3 pin alone. An exact patch version is required: p4a
# resolves this to a CPython git tag (https://github.com/python/cpython/
# archive/refs/tags/v<version>.tar.gz) and "v3.11" alone is not a real tag.
# The Android backend uses python-for-Android's SDL2 bootstrap and pyjnius,
# but it does not use Kivy. Including Kivy pulls its native widgets and
# lifecycle into the APK even though pywebview owns the Android lifecycle.
DEFAULT_REQUIREMENTS = 'python3==3.11.9,hostpython3==3.11.9,pywebview2'

DEFAULT_APP_SECTION = {
    'source.include_exts': 'py,png,jpg,kv,atlas,html,jar,css,js',
    'source.exclude_dirs': 'bin,build,dist,installers,__pycache__,.git',
    'android.permissions': 'INTERNET',
    # Without this, a fresh Android SDK triggers an interactive license
    # prompt on first build that blocks forever with no stdin (e.g. in CI).
    'android.accept_sdk_license': 'True',
    # Pinned to a released python-for-android version rather than tracking
    # master HEAD: master is a moving target and pulls in whatever the
    # newest available toolchain releases happen to be that day (observed:
    # a broken PyPI pip self-upgrade breaking p4a's own pip bootstrap step).
    # A tagged release is a coherent, previously-tested snapshot instead.
    'p4a.branch': 'v2026.05.09',
}


class AndroidBuildError(Exception):
    pass


def _split_identifier(identifier: str) -> tuple[str, str]:
    parts = identifier.split('.')
    if len(parts) < 2:
        raise AndroidBuildError(
            f'identifier "{identifier}" must be reverse-DNS (e.g. com.example.app) '
            'for Android packaging'
        )
    return '.'.join(parts[:-1]), parts[-1]


def write_buildozer_spec(config: dict[str, Any], project_dir: str) -> str:
    """
    Renders buildozer.spec as a dict merged with user overrides (rather than
    string-templating) so bundle.mobile.android.buildozerSpecOverrides can
    safely replace any default key -- including ones like
    android.permissions or icon.filename -- without producing duplicate INI
    keys, which buildozer's strict configparser would reject.
    """
    from webview.util import android_jar_path

    package_domain, package_name = _split_identifier(config['identifier'])
    android_cfg = config.get('mobile', {}).get('android', {})
    overrides = dict(android_cfg.get('buildozerSpecOverrides', {}))

    icon = config.get('bundle', {}).get('icon')

    app_section = {
        'title': config['productName'],
        'package.name': package_name,
        'package.domain': package_domain,
        'source.dir': '.',
        'version': config['version'],
        'requirements': DEFAULT_REQUIREMENTS,
        'android.add_jars': android_jar_path(),
        **DEFAULT_APP_SECTION,
    }
    if icon:
        app_section['icon.filename'] = f'{icon}.png'

    app_section.update(overrides)

    parser = configparser.ConfigParser()
    parser['app'] = app_section
    parser['buildozer'] = {'log_level': '2'}

    spec_path = os.path.join(project_dir, 'buildozer.spec')
    with open(spec_path, 'w', encoding='utf-8') as f:
        parser.write(f)

    return spec_path


def build(config: dict[str, Any], project_dir: str, release: bool = False) -> str:
    """
    Write buildozer.spec and run `buildozer android debug|release`. Returns
    the path to the produced .apk. Requires buildozer plus the Android
    SDK/NDK/Java to actually be installed -- run `pywebview2 doctor` to check.
    """
    entry_name = os.path.basename(config['entry'])
    if entry_name != 'main.py':
        raise AndroidBuildError(
            f'buildozer requires the entry point to be named main.py (found "{entry_name}"). '
            'Rename your entry point or add a main.py that imports it.'
        )

    spec_path = write_buildozer_spec(config, project_dir)

    buildozer = shutil.which('buildozer')
    if not buildozer:
        raise AndroidBuildError(
            f'buildozer not found on PATH. Wrote {spec_path}; install buildozer '
            '(pip install buildozer) plus the Android SDK/NDK/Java to build the .apk.'
        )

    target = 'release' if release else 'debug'
    subprocess.run([buildozer, 'android', target], cwd=project_dir, check=True)

    bin_dir = os.path.join(project_dir, 'bin')
    if not os.path.isdir(bin_dir):
        raise AndroidBuildError(f'buildozer did not produce a bin/ directory in {project_dir}')

    apks = sorted(f for f in os.listdir(bin_dir) if f.endswith('.apk'))
    if not apks:
        raise AndroidBuildError(f'No .apk found in {bin_dir}')

    return os.path.join(bin_dir, apks[-1])
