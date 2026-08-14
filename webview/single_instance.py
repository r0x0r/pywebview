"""
(C) 2014-2019 Roman Sirokov and contributors
Licensed under BSD license

http://github.com/r0x0r/pywebview/

Single-instance enforcement: detect whether another instance of the app is
already running and, if so, forward this launch's command-line arguments to
it instead of starting a second copy. Uses multiprocessing.connection
(stdlib only, no new dependency) for cross-process IPC -- a named pipe on
Windows, a Unix domain socket elsewhere.
"""

from __future__ import annotations

import hashlib
import os
import sys
import threading
from multiprocessing.connection import Client, Connection, Listener
from typing import Callable

from webview.errors import WebViewException
from webview.util import app_data_dir


def _address(identifier: str) -> str:
    if sys.platform == 'win32':
        return f'\\\\.\\pipe\\{identifier}'
    return os.path.join(app_data_dir(), f'{identifier}.sock')


def _authkey(identifier: str) -> bytes:
    # Both the primary and the second-launch process need the *same* authkey
    # for the multiprocessing.connection handshake to succeed -- they are
    # separate OS processes, each with its own random default authkey, so
    # one must be derived deterministically from `identifier` instead.
    return hashlib.sha256(f'pywebview-single-instance-{identifier}'.encode()).digest()


def _try_connect(address: str, authkey: bytes) -> Connection | None:
    try:
        return Client(address, authkey=authkey)
    except (ConnectionRefusedError, FileNotFoundError, OSError):
        return None


def enforce_single_instance(
    on_second_instance: Callable[[list[str]], None] | None = None,
    identifier: str = 'pywebview',
) -> bool:
    """
    Ensure only one instance of the app is running at a time.

    Call this near the start of your app, before creating any windows. If it
    returns False, another instance is already running and this launch's
    sys.argv has already been forwarded to that instance's
    on_second_instance callback (if one was registered when it called this
    function) -- the caller should return/exit without creating any windows.
    If it returns True, this is the primary instance: a background thread is
    started to listen for and forward future second-launch attempts to
    on_second_instance.

    :param on_second_instance: Callback invoked (only in the primary
        instance) with the second launch's sys.argv, whenever another
        instance of the app is started while this one is still running. A
        common use is to bring the app's window to the front.
    :param identifier: Unique identifier for this app, used to derive the
        IPC address. Must be the same across launches you want to treat as
        the same app.
    :return: True if this is the primary instance, False otherwise.
    """
    address = _address(identifier)
    authkey = _authkey(identifier)

    conn = _try_connect(address, authkey)
    if conn is not None:
        try:
            conn.send(sys.argv)
        finally:
            conn.close()
        return False

    if sys.platform != 'win32':
        os.makedirs(app_data_dir(), exist_ok=True)
        # A stale socket file from a crashed previous instance makes bind()
        # fail with "address already in use" even though nothing is
        # listening -- the failed connect attempt above already confirmed
        # no one is actually there, so it's safe to remove it.
        try:
            os.unlink(address)
        except FileNotFoundError:
            pass

    try:
        listener = Listener(address, authkey=authkey)
    except OSError:
        # Lost a race with another process that became primary between our
        # failed connect attempt and now -- retry as a client once.
        conn = _try_connect(address, authkey)
        if conn is not None:
            try:
                conn.send(sys.argv)
            finally:
                conn.close()
            return False
        raise WebViewException(f'Failed to establish single-instance IPC on {address!r}')

    def _accept_loop() -> None:
        while True:
            try:
                incoming = listener.accept()
            except OSError:
                return

            try:
                argv = incoming.recv()
                if on_second_instance:
                    on_second_instance(argv)
            except EOFError:
                pass
            finally:
                incoming.close()

    threading.Thread(target=_accept_loop, daemon=True).start()
    return True
