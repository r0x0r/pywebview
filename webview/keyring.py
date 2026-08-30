"""
(C) 2014-2019 Roman Sirokov and contributors
Licensed under BSD license

http://github.com/imattau/pywebview2/

Cross-platform secure credential storage, backed by each OS's native
mechanism: macOS Keychain, Windows DPAPI, and Linux Secret Service (with an
encrypted-file fallback when no Secret Service implementation is available).
"""

from __future__ import annotations

import hashlib
import os
import sys

from webview.errors import WebViewException
from webview.util import app_data_dir

_SERVICE_LABEL = 'pywebview2'


def set_password(service: str, username: str, password: str) -> None:
    """
    Store a password in the OS-native secure credential store.

    :param service: Name of the service/application the credential belongs to.
    :param username: Username or account identifier associated with the credential.
    :param password: Secret value to store.
    """
    if sys.platform == 'darwin':
        _macos_set_password(service, username, password)
    elif sys.platform == 'win32':
        _windows_set_password(service, username, password)
    elif sys.platform.startswith('linux'):
        _linux_set_password(service, username, password)
    else:
        raise WebViewException(f'Keyring is not supported on platform {sys.platform!r}')


def get_password(service: str, username: str) -> str | None:
    """
    Retrieve a password from the OS-native secure credential store.

    :param service: Name of the service/application the credential belongs to.
    :param username: Username or account identifier associated with the credential.
    :return: The stored password, or None if no credential is found.
    """
    if sys.platform == 'darwin':
        return _macos_get_password(service, username)
    elif sys.platform == 'win32':
        return _windows_get_password(service, username)
    elif sys.platform.startswith('linux'):
        return _linux_get_password(service, username)
    else:
        raise WebViewException(f'Keyring is not supported on platform {sys.platform!r}')


def delete_password(service: str, username: str) -> None:
    """
    Delete a password from the OS-native secure credential store. No-op if the
    credential does not exist.

    :param service: Name of the service/application the credential belongs to.
    :param username: Username or account identifier associated with the credential.
    """
    if sys.platform == 'darwin':
        _macos_delete_password(service, username)
    elif sys.platform == 'win32':
        _windows_delete_password(service, username)
    elif sys.platform.startswith('linux'):
        _linux_delete_password(service, username)
    else:
        raise WebViewException(f'Keyring is not supported on platform {sys.platform!r}')


# -- macOS: Keychain, via the Security framework already declared as a dependency ---------


def _macos_set_password(service: str, username: str, password: str) -> None:
    from Security import (
        SecItemAdd,
        SecItemCopyMatching,
        SecItemUpdate,
        errSecItemNotFound,
        errSecSuccess,
        kSecAttrAccount,
        kSecAttrService,
        kSecClass,
        kSecClassGenericPassword,
        kSecValueData,
    )

    query = {
        kSecClass: kSecClassGenericPassword,
        kSecAttrService: service,
        kSecAttrAccount: username,
    }
    status, _ = SecItemCopyMatching(query, None)

    if status == errSecItemNotFound:
        item = dict(query)
        item[kSecValueData] = password.encode('utf-8')
        status, _ = SecItemAdd(item, None)
    else:
        status = SecItemUpdate(query, {kSecValueData: password.encode('utf-8')})

    if status != errSecSuccess:
        raise WebViewException(f'Failed to store password in Keychain (status {status})')


def _macos_get_password(service: str, username: str) -> str | None:
    from Security import (
        SecItemCopyMatching,
        errSecItemNotFound,
        errSecSuccess,
        kSecAttrAccount,
        kSecAttrService,
        kSecClass,
        kSecClassGenericPassword,
        kSecMatchLimit,
        kSecMatchLimitOne,
        kSecReturnData,
    )

    query = {
        kSecClass: kSecClassGenericPassword,
        kSecAttrService: service,
        kSecAttrAccount: username,
        kSecReturnData: True,
        kSecMatchLimit: kSecMatchLimitOne,
    }
    status, result = SecItemCopyMatching(query, None)

    if status == errSecItemNotFound:
        return None
    if status != errSecSuccess:
        raise WebViewException(f'Failed to read password from Keychain (status {status})')
    if result is None:
        return None

    return bytes(result).decode('utf-8')


def _macos_delete_password(service: str, username: str) -> None:
    from Security import (
        SecItemDelete,
        errSecItemNotFound,
        errSecSuccess,
        kSecAttrAccount,
        kSecAttrService,
        kSecClass,
        kSecClassGenericPassword,
    )

    query = {
        kSecClass: kSecClassGenericPassword,
        kSecAttrService: service,
        kSecAttrAccount: username,
    }
    status = SecItemDelete(query)
    if status not in (errSecSuccess, errSecItemNotFound):
        raise WebViewException(f'Failed to delete password from Keychain (status {status})')


# -- Windows: DPAPI (via pythonnet, already a dependency) + an encrypted file --------------


def _windows_data_dir() -> str:
    path = os.path.join(app_data_dir(), 'keyring')
    os.makedirs(path, exist_ok=True)
    return path


def _windows_key_path(service: str, username: str) -> str:
    digest = hashlib.sha256(f'{service}\x00{username}'.encode()).hexdigest()
    return os.path.join(_windows_data_dir(), f'{digest}.bin')


def _windows_dpapi():
    try:
        import clr

        clr.AddReference('System.Security')
        from System import Array, Byte
        from System.Security.Cryptography import DataProtectionScope, ProtectedData
    except ImportError as e:
        raise WebViewException('Keyring requires pythonnet on Windows.') from e

    return Array, Byte, DataProtectionScope, ProtectedData


def _windows_set_password(service: str, username: str, password: str) -> None:
    Array, Byte, DataProtectionScope, ProtectedData = _windows_dpapi()

    data = Array[Byte](password.encode('utf-8'))
    protected = ProtectedData.Protect(data, None, DataProtectionScope.CurrentUser)

    with open(_windows_key_path(service, username), 'wb') as f:
        f.write(bytes(protected))


def _windows_get_password(service: str, username: str) -> str | None:
    path = _windows_key_path(service, username)
    if not os.path.exists(path):
        return None

    Array, Byte, DataProtectionScope, ProtectedData = _windows_dpapi()

    with open(path, 'rb') as f:
        encrypted = f.read()

    data = Array[Byte](encrypted)
    try:
        unprotected = ProtectedData.Unprotect(data, None, DataProtectionScope.CurrentUser)
    except Exception as e:
        raise WebViewException(f'Failed to decrypt stored password: {e}') from e

    return bytes(unprotected).decode('utf-8')


def _windows_delete_password(service: str, username: str) -> None:
    path = _windows_key_path(service, username)
    if os.path.exists(path):
        os.remove(path)


# -- Linux: Secret Service (via libsecret, if the system typelib is present) ---------------
# with an encrypted-file fallback (via the `cryptography` package, `pip install
# pywebview2[keyring]`) when no Secret Service implementation is reachable.

_secret_schema = None


def _linux_get_secret_schema():
    global _secret_schema
    from gi.repository import Secret

    if _secret_schema is None:
        _secret_schema = Secret.Schema.new(
            'org.pywebview2.Password',
            Secret.SchemaFlags.NONE,
            {
                'service': Secret.SchemaAttributeType.STRING,
                'username': Secret.SchemaAttributeType.STRING,
            },
        )
    return _secret_schema


def _linux_secret_service():
    try:
        import gi

        gi.require_version('Secret', '1')
        from gi.repository import Secret

        return Secret
    except (ImportError, ValueError):
        return None


def _linux_set_password(service: str, username: str, password: str) -> None:
    Secret = _linux_secret_service()
    if Secret is not None:
        schema = _linux_get_secret_schema()
        label = f'{_SERVICE_LABEL}: {service} ({username})'
        Secret.password_store_sync(
            schema,
            {'service': service, 'username': username},
            Secret.COLLECTION_DEFAULT,
            label,
            password,
            None,
        )
        return

    _linux_set_password_file(service, username, password)


def _linux_get_password(service: str, username: str) -> str | None:
    Secret = _linux_secret_service()
    if Secret is not None:
        schema = _linux_get_secret_schema()
        return Secret.password_lookup_sync(schema, {'service': service, 'username': username}, None)

    return _linux_get_password_file(service, username)


def _linux_delete_password(service: str, username: str) -> None:
    Secret = _linux_secret_service()
    if Secret is not None:
        schema = _linux_get_secret_schema()
        Secret.password_clear_sync(schema, {'service': service, 'username': username}, None)
        return

    _linux_delete_password_file(service, username)


def _linux_fallback_dir() -> str:
    path = os.path.join(app_data_dir(), 'keyring')
    os.makedirs(path, mode=0o700, exist_ok=True)
    return path


def _linux_fallback_key() -> bytes:
    key_path = os.path.join(_linux_fallback_dir(), '.key')
    if os.path.exists(key_path):
        with open(key_path, 'rb') as f:
            return f.read()

    try:
        from cryptography.fernet import Fernet
    except ImportError as e:
        raise _linux_keyring_unavailable_error() from e

    key = Fernet.generate_key()
    fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(key)
    return key


def _linux_fallback_path(service: str, username: str) -> str:
    digest = hashlib.sha256(f'{service}\x00{username}'.encode()).hexdigest()
    return os.path.join(_linux_fallback_dir(), f'{digest}.bin')


def _linux_keyring_unavailable_error() -> WebViewException:
    return WebViewException(
        'No Secret Service implementation found and the cryptography package is not '
        'installed for the encrypted-file fallback. Install libsecret (e.g. the '
        '"gir1.2-secret-1" system package) or run "pip install pywebview2[keyring]".'
    )


def _linux_set_password_file(service: str, username: str, password: str) -> None:
    try:
        from cryptography.fernet import Fernet
    except ImportError as e:
        raise _linux_keyring_unavailable_error() from e

    fernet = Fernet(_linux_fallback_key())
    token = fernet.encrypt(password.encode('utf-8'))

    path = _linux_fallback_path(service, username)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(token)


def _linux_get_password_file(service: str, username: str) -> str | None:
    path = _linux_fallback_path(service, username)
    if not os.path.exists(path):
        return None

    try:
        from cryptography.fernet import Fernet, InvalidToken
    except ImportError as e:
        raise _linux_keyring_unavailable_error() from e

    fernet = Fernet(_linux_fallback_key())
    with open(path, 'rb') as f:
        token = f.read()

    try:
        return fernet.decrypt(token).decode('utf-8')
    except InvalidToken as e:
        raise WebViewException(
            'Failed to decrypt stored password (key mismatch or corrupted data)'
        ) from e


def _linux_delete_password_file(service: str, username: str) -> None:
    path = _linux_fallback_path(service, username)
    if os.path.exists(path):
        os.remove(path)
