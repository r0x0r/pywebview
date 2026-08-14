"""
(C) 2014-2019 Roman Sirokov and contributors
Licensed under BSD license

http://github.com/r0x0r/pywebview/

A simple JSON-backed persistent key-value store for application settings,
distinct from webview.keyring (which is for secrets, not plain preferences).
"""

from __future__ import annotations

import json
import os
import threading
from typing import Any

from webview.errors import WebViewException
from webview.util import app_data_dir

_MISSING = object()


class Store:
    """
    A JSON-backed key-value store. Reads the whole file into memory on
    creation and writes it back out on every mutation, which is fine for
    the small amounts of app-settings data this is meant for.
    """

    def __init__(self, path: str | None = None) -> None:
        self.path = path or os.path.join(app_data_dir(), 'store.json')
        self._lock = threading.Lock()
        self._data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if not os.path.exists(self.path):
            return {}

        with open(self.path, encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                raise WebViewException(f'Store file {self.path} contains invalid JSON: {e}') from e

        if not isinstance(data, dict):
            raise WebViewException(f'Store file {self.path} does not contain a JSON object')

        return data

    def _save(self) -> None:
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        tmp_path = f'{self.path}.tmp'
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, indent=2, sort_keys=True)
        os.replace(tmp_path, self.path)

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = value
            self._save()

    def has(self, key: str) -> bool:
        with self._lock:
            return key in self._data

    def delete(self, key: str) -> None:
        with self._lock:
            if key in self._data:
                del self._data[key]
                self._save()

    def keys(self) -> list[str]:
        with self._lock:
            return list(self._data.keys())

    def clear(self) -> None:
        with self._lock:
            self._data = {}
            self._save()


_default_store: Store | None = None


def _get_default_store() -> Store:
    global _default_store
    if _default_store is None:
        _default_store = Store()
    return _default_store


def get(key: str, default: Any = None) -> Any:
    """Get a value from the default store. Returns `default` if the key does not exist."""
    return _get_default_store().get(key, default)


def set(key: str, value: Any) -> None:
    """Set a value in the default store. `value` must be JSON-serializable."""
    _get_default_store().set(key, value)


def has(key: str) -> bool:
    """Check whether a key exists in the default store."""
    return _get_default_store().has(key)


def delete(key: str) -> None:
    """Delete a key from the default store. No-op if the key does not exist."""
    _get_default_store().delete(key)


def keys() -> list[str]:
    """List all keys currently in the default store."""
    return _get_default_store().keys()


def clear() -> None:
    """Remove all keys from the default store."""
    _get_default_store().clear()
