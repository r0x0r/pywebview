"""
Loader and validator for pywebview2.conf.json.
"""

from __future__ import annotations

import json
import os
from typing import Any

CONFIG_FILENAME = 'pywebview2.conf.json'

DEFAULT_CONFIG: dict[str, Any] = {
    'productName': 'MyApp',
    'version': '0.1.0',
    'identifier': 'com.example.myapp',
    'entry': 'main.py',
    'frontendDist': 'frontend',
    'frontendDev': {
        'command': None,
        'url': None,
        'watch': ['frontend'],
    },
    'window': {
        'title': 'MyApp',
        'width': 1024,
        'height': 768,
        'resizable': True,
        'frameless': False,
    },
    'bundle': {
        'targets': [],
        'icon': None,
        'resources': [],
        'pyinstaller': {
            'onefile': False,
            'excludes': [],
            'extraArgs': [],
        },
        'windows': {
            'webview2RuntimePath': None,
            'webview2InstallMode': 'downloadBootstrapper',
        },
        'linux': {
            'webkitgtkPackage': 'gir1.2-webkit2-4.1',
            'debDepends': ['libwebkit2gtk-4.1-0'],
        },
        'macos': {
            'minimumSystemVersion': '11.0',
            'signingIdentity': None,
            'entitlements': None,
        },
    },
    'mobile': {
        'android': {'buildozerSpecOverrides': {}},
        'ios': {'enabled': False},
    },
}

REQUIRED_TOP_LEVEL_KEYS = ('productName', 'version', 'identifier', 'entry')


class ConfigError(Exception):
    pass


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def find_config(start_dir: str | None = None) -> str | None:
    """Look for pywebview2.conf.json in start_dir (default cwd)."""
    directory = start_dir or os.getcwd()
    path = os.path.join(directory, CONFIG_FILENAME)
    return path if os.path.exists(path) else None


def load(path: str | None = None) -> dict[str, Any]:
    """
    Load and validate pywebview2.conf.json, merging it over DEFAULT_CONFIG so
    partial configs are valid. Raises ConfigError on missing file or invalid JSON.
    """
    config_path = path or find_config()
    if not config_path or not os.path.exists(config_path):
        raise ConfigError(
            f'{CONFIG_FILENAME} not found. Run `pywebview2 init` to create a new project.'
        )

    with open(config_path, encoding='utf-8') as f:
        try:
            raw = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigError(f'Invalid JSON in {config_path}: {e}') from e

    raw.pop('$schema', None)
    config = _deep_merge(DEFAULT_CONFIG, raw)
    validate(config)
    return config


def validate(config: dict[str, Any]) -> None:
    missing = [key for key in REQUIRED_TOP_LEVEL_KEYS if not config.get(key)]
    if missing:
        raise ConfigError(f'Missing required config keys: {", ".join(missing)}')

    valid_targets = {'msi', 'nsis', 'dmg', 'deb', 'appimage', 'android'}
    targets = config.get('bundle', {}).get('targets', [])
    invalid = set(targets) - valid_targets
    if invalid:
        raise ConfigError(
            f'Invalid bundle.targets entries: {", ".join(sorted(invalid))}. '
            f'Valid targets: {", ".join(sorted(valid_targets))}'
        )
