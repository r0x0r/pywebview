"""
Linux packaging: .deb via dpkg-deb, AppImage via appimagetool.

WebKitGTK cannot be bundled (system package with its own native deps), so
.deb declares it as a Depends: entry and AppImage can only warn that it must
already be present on the target system.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from typing import Any

from webview.bundler._templating import render

logger_prefix = '[pywebview2 build]'


class InstallerError(Exception):
    pass


def _package_name(product_name: str) -> str:
    return product_name.lower().replace(' ', '-')


def _find_executable(source_dir: str, product_name: str) -> str:
    candidate = os.path.join(source_dir, product_name)
    if os.path.exists(candidate) and os.access(candidate, os.X_OK):
        return product_name
    for name in os.listdir(source_dir):
        path = os.path.join(source_dir, name)
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return name
    raise InstallerError(f'No executable found in {source_dir}')


def build_deb(config: dict[str, Any], source_dir: str, output_dir: str) -> str:
    product_name = config['productName']
    package_name = _package_name(product_name)
    exe_name = _find_executable(source_dir, product_name)

    os.makedirs(output_dir, exist_ok=True)
    staging_dir = os.path.join(output_dir, f'{package_name}-deb')
    if os.path.exists(staging_dir):
        shutil.rmtree(staging_dir)

    install_dir = os.path.join(staging_dir, 'opt', package_name)
    bin_dir = os.path.join(staging_dir, 'usr', 'bin')
    debian_dir = os.path.join(staging_dir, 'DEBIAN')
    applications_dir = os.path.join(staging_dir, 'usr', 'share', 'applications')
    for d in (install_dir, bin_dir, debian_dir, applications_dir):
        os.makedirs(d, exist_ok=True)

    shutil.copytree(source_dir, install_dir, dirs_exist_ok=True)

    launcher_path = os.path.join(bin_dir, package_name)
    with open(launcher_path, 'w', encoding='utf-8') as f:
        f.write(f'#!/bin/sh\nexec "/opt/{package_name}/{exe_name}" "$@"\n')
    os.chmod(
        launcher_path, os.stat(launcher_path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH
    )

    linux_cfg = config['bundle'].get('linux', {})
    control_content = render(
        'control.jinja',
        package_name=package_name,
        version=config['version'],
        architecture='amd64',
        depends=', '.join(linux_cfg.get('debDepends', [])) or 'libc6',
        product_name=product_name,
    )
    with open(os.path.join(debian_dir, 'control'), 'w', encoding='utf-8') as f:
        f.write(control_content)

    desktop_content = render(
        'app.desktop.jinja',
        product_name=product_name,
        exec_name=package_name,
        icon_name=package_name,
    )
    with open(
        os.path.join(applications_dir, f'{package_name}.desktop'), 'w', encoding='utf-8'
    ) as f:
        f.write(desktop_content)

    deb_path = os.path.join(output_dir, f'{package_name}_{config['version']}_amd64.deb')

    if not shutil.which('dpkg-deb'):
        raise InstallerError(
            f'dpkg-deb not found on PATH. Staged package at {staging_dir}; '
            'install dpkg-deb to build the .deb.'
        )
    subprocess.run(['dpkg-deb', '--build', '--root-owner-group', staging_dir, deb_path], check=True)

    return deb_path


def build_appimage(config: dict[str, Any], source_dir: str, output_dir: str) -> str:
    product_name = config['productName']
    package_name = _package_name(product_name)
    exe_name = _find_executable(source_dir, product_name)

    os.makedirs(output_dir, exist_ok=True)
    appdir = os.path.join(output_dir, f'{package_name}.AppDir')
    if os.path.exists(appdir):
        shutil.rmtree(appdir)

    usr_bin = os.path.join(appdir, 'usr', 'bin')
    os.makedirs(usr_bin, exist_ok=True)
    shutil.copytree(source_dir, usr_bin, dirs_exist_ok=True)

    apprun_path = os.path.join(appdir, 'AppRun')
    with open(apprun_path, 'w', encoding='utf-8') as f:
        f.write(
            f'#!/bin/sh\nHERE=$(dirname "$(readlink -f "$0")")\nexec "$HERE/usr/bin/{exe_name}" "$@"\n'
        )
    os.chmod(apprun_path, os.stat(apprun_path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    desktop_content = render(
        'app.desktop.jinja',
        product_name=product_name,
        exec_name=exe_name,
        icon_name=package_name,
    )
    with open(os.path.join(appdir, f'{package_name}.desktop'), 'w', encoding='utf-8') as f:
        f.write(desktop_content)

    print(
        f'{logger_prefix} WARNING: WebKitGTK cannot be bundled inside an AppImage. '
        'The target system must already have it installed.'
    )

    appimagetool = shutil.which('appimagetool')
    if not appimagetool:
        raise InstallerError(
            f'appimagetool not found on PATH. Staged AppDir at {appdir}; '
            'install appimagetool to build the AppImage.'
        )

    appimage_path = os.path.join(output_dir, f'{package_name}-{config['version']}-x86_64.AppImage')
    subprocess.run([appimagetool, appdir, appimage_path], check=True)

    return appimage_path
