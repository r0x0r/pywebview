"""
PyInstaller orchestration: turn a pywebview.conf.json + project dir into a
frozen executable. Relies on webview/__pyinstaller/hook-webview.py being
auto-discovered via the `pyinstaller40.hook-dirs` entry point already
registered in pyproject.toml -- this module never touches that hook directly.
"""

from __future__ import annotations

import os
from typing import Any


class FreezeError(Exception):
    pass


def build_pyinstaller_args(config: dict[str, Any], project_dir: str, dist_dir: str) -> list[str]:
    bundle = config['bundle']
    pyinstaller_cfg = bundle.get('pyinstaller', {})

    entry = os.path.join(project_dir, config['entry'])
    args = [
        entry,
        '--name',
        config['productName'],
        '--distpath',
        dist_dir,
        '--workpath',
        os.path.join(dist_dir, '.work'),
        '--specpath',
        os.path.join(dist_dir, '.spec'),
        '--noconfirm',
    ]

    if pyinstaller_cfg.get('onefile'):
        args.append('--onefile')
    else:
        args.append('--onedir')

    icon = bundle.get('icon')
    if icon:
        ico_path = f'{icon}.ico' if not icon.endswith(('.ico', '.icns')) else icon
        if os.path.exists(os.path.join(project_dir, ico_path)):
            args += ['--icon', os.path.join(project_dir, ico_path)]

    for resource in bundle.get('resources', []):
        resource_path = os.path.join(project_dir, resource.rstrip('/*'))
        if os.path.exists(resource_path):
            sep = ';' if os.name == 'nt' else ':'
            dest = os.path.relpath(resource_path, project_dir)
            args += ['--add-data', f'{resource_path}{sep}{dest}']

    for exclude in pyinstaller_cfg.get('excludes', []):
        args += ['--exclude-module', exclude]

    args += pyinstaller_cfg.get('extraArgs', [])

    return args


def freeze(config: dict[str, Any], project_dir: str, dist_dir: str) -> str:
    """
    Run PyInstaller against the project's entry point. Returns the path to
    the frozen app directory/executable produced by PyInstaller.
    """
    try:
        import PyInstaller.__main__
    except ImportError as e:
        raise FreezeError(
            'PyInstaller is not installed. Install it with `pip install pyinstaller`.'
        ) from e

    entry_path = os.path.join(project_dir, config['entry'])
    if not os.path.exists(entry_path):
        raise FreezeError(f'Entry point not found: {entry_path}')

    os.makedirs(dist_dir, exist_ok=True)
    args = build_pyinstaller_args(config, project_dir, dist_dir)

    PyInstaller.__main__.run(args)

    output_path = os.path.join(dist_dir, config['productName'])
    if not os.path.exists(output_path):
        raise FreezeError(f'PyInstaller did not produce expected output at {output_path}')

    return output_path
