"""
macOS installer generation: assemble a .app bundle from PyInstaller output,
then package it as a .dmg via hdiutil (built into macOS, no external tool).
"""

from __future__ import annotations

import os
import plistlib
import shutil
import subprocess
from typing import Any


class InstallerError(Exception):
    pass


def build_app_bundle(config: dict[str, Any], source_dir: str, output_dir: str) -> str:
    """
    If PyInstaller already produced a .app (macOS target), use it directly.
    Otherwise assemble a minimal .app bundle around the onedir/onefile output.
    """
    product_name = config['productName']
    os.makedirs(output_dir, exist_ok=True)

    existing_app = os.path.join(os.path.dirname(source_dir), f'{product_name}.app')
    if os.path.isdir(existing_app):
        return existing_app

    app_path = os.path.join(output_dir, f'{product_name}.app')
    if os.path.exists(app_path):
        shutil.rmtree(app_path)

    contents = os.path.join(app_path, 'Contents')
    macos_dir = os.path.join(contents, 'MacOS')
    resources_dir = os.path.join(contents, 'Resources')
    os.makedirs(macos_dir, exist_ok=True)
    os.makedirs(resources_dir, exist_ok=True)

    for name in os.listdir(source_dir):
        src = os.path.join(source_dir, name)
        dest = os.path.join(macos_dir, name)
        if os.path.isdir(src):
            shutil.copytree(src, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dest)

    executables = [
        n for n in os.listdir(source_dir) if os.access(os.path.join(source_dir, n), os.X_OK)
    ]
    executable_name = (
        product_name
        if product_name in executables
        else (executables[0] if executables else product_name)
    )

    icon = config['bundle'].get('icon')
    icon_file = None
    if icon:
        icns_path = f'{icon}.icns' if not icon.endswith('.icns') else icon
        if os.path.exists(icns_path):
            icon_file = os.path.basename(icns_path)
            shutil.copy2(icns_path, os.path.join(resources_dir, icon_file))

    info_plist = {
        'CFBundleName': product_name,
        'CFBundleDisplayName': product_name,
        'CFBundleIdentifier': config['identifier'],
        'CFBundleVersion': config['version'],
        'CFBundleShortVersionString': config['version'],
        'CFBundleExecutable': executable_name,
        'CFBundlePackageType': 'APPL',
        'LSMinimumSystemVersion': config['bundle']
        .get('macos', {})
        .get('minimumSystemVersion', '11.0'),
    }
    if icon_file:
        info_plist['CFBundleIconFile'] = icon_file

    with open(os.path.join(contents, 'Info.plist'), 'wb') as f:
        plistlib.dump(info_plist, f)

    return app_path


def build_dmg(config: dict[str, Any], app_path: str, output_dir: str) -> str:
    product_name = config['productName']
    os.makedirs(output_dir, exist_ok=True)
    dmg_path = os.path.join(output_dir, f'{product_name}.dmg')

    if not shutil.which('hdiutil'):
        raise InstallerError('hdiutil not found -- .dmg packaging is only available on macOS.')

    staging_dir = os.path.join(output_dir, '.dmg-staging')
    if os.path.exists(staging_dir):
        shutil.rmtree(staging_dir)
    os.makedirs(staging_dir)
    shutil.copytree(app_path, os.path.join(staging_dir, os.path.basename(app_path)))
    os.symlink('/Applications', os.path.join(staging_dir, 'Applications'))

    if os.path.exists(dmg_path):
        os.remove(dmg_path)

    subprocess.run(
        [
            'hdiutil',
            'create',
            '-volname',
            product_name,
            '-srcfolder',
            staging_dir,
            '-ov',
            '-format',
            'UDZO',
            dmg_path,
        ],
        check=True,
    )
    shutil.rmtree(staging_dir)

    return dmg_path
