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
    'frontendBuild': {
        'command': None,
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
        'ios': {
            'enabled': False,
            'deploymentTarget': '15.0',
            'scheme': None,
            'signingTeam': None,
            'exportMethod': 'development',
        },
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

    if not isinstance(raw, dict):
        raise ConfigError(f'Configuration root in {config_path} must be a JSON object')

    raw.pop('$schema', None)
    config = _deep_merge(DEFAULT_CONFIG, raw)
    validate(config)
    return config


def validate(config: dict[str, Any]) -> None:
    missing = [key for key in REQUIRED_TOP_LEVEL_KEYS if not config.get(key)]
    if missing:
        raise ConfigError(f"Missing required config keys: {', '.join(missing)}")

    valid_targets = {'msi', 'nsis', 'dmg', 'deb', 'appimage', 'android', 'ios'}
    bundle = config.get('bundle', {})
    if not isinstance(bundle, dict):
        raise ConfigError('bundle must be an object')
    targets = bundle.get('targets', [])
    if not isinstance(targets, list) or not all(isinstance(target, str) for target in targets):
        raise ConfigError('bundle.targets must be an array of strings')
    invalid = set(targets) - valid_targets
    if invalid:
        raise ConfigError(
            f"Invalid bundle.targets entries: {', '.join(sorted(invalid))}. "
            f"Valid targets: {', '.join(sorted(valid_targets))}"
        )

    identifier = config.get('identifier', '')
    identifier_parts = identifier.split('.') if isinstance(identifier, str) else []
    if len(identifier_parts) < 2 or any(
        not part or not (part[0].isalnum() and part[-1].isalnum()) for part in identifier_parts
    ):
        raise ConfigError('identifier must use reverse-DNS notation, e.g. com.example.app')

    frontend_build = config.get('frontendBuild', {})
    if not isinstance(frontend_build, dict) or not isinstance(
        frontend_build.get('command'), (str, type(None))
    ):
        raise ConfigError('frontendBuild.command must be a string or null')
