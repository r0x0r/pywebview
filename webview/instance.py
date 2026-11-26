"""
Launches of the application: the files and URLs a launch asks to open, and single instance mode.

Files and URLs are delivered with webview.events.opened, after webview.events.started. They come
from the command line, from the backends (macOS Apple Events, Android intents), and in single
instance mode from later launches.

In single instance mode, a second launch of the application hands its command line to the running
instance and exits, instead of opening windows of its own.

The running instance listens on a named pipe (Windows) or a Unix socket (macOS, Linux), whose
address is derived from the instance id and the user name, so that instances of different users
do not see each other. On macOS and Linux, the running instance also holds a lock on a file next
to the socket for its lifetime. The operating system releases the lock when a process exits, so a
socket whose lock is free was left behind by an instance that crashed and is replaced. Messages
are JSON, never pickles, so a connecting process cannot run code in the running instance.

webview.events is reached through the webview module at call time, as this module is imported by
it.
"""

from __future__ import annotations

import atexit
import contextlib
import getpass
import hashlib
import json
import logging
import os
import queue
import re
import sys
import tempfile
import threading
import time
from collections.abc import Iterator
from multiprocessing.connection import Client, Connection, Listener
from typing import TYPE_CHECKING
from urllib.parse import urlparse
from urllib.request import url2pathname

if TYPE_CHECKING:
    from webview.window import Window

logger = logging.getLogger('pywebview')

_MAX_MESSAGE_SIZE = 1024 * 1024
_CONNECT_ATTEMPTS = 10
_HAND_OVER_TIMEOUT = 10
# sun_path holds 104 bytes on macOS and 108 on Linux, including the terminating null
_MAX_SOCKET_PATH = 103

# Only URLs with an authority, e.g. myapp://item/1, so that arguments such as key:value are not
# mistaken for URLs. Schemes need two characters, as single letters are Windows drive letters.
_URL = re.compile(r'[A-Za-z][A-Za-z0-9+.-]+://\S')

_argv_opened = False
_open_requests: queue.SimpleQueue = queue.SimpleQueue()
_open_worker: threading.Thread | None = None
_open_lock = threading.Lock()

# The running instance's listener is process-wide
_listener: Listener | None = None
_lock_fd: int | None = None
_launch_lock = threading.Lock()

_lock_file: str | None = None

def fire_started(window: Window) -> None:
    """Fire webview.events.started in the background, once the first window is shown."""
    threading.Thread(target=_fire_started, args=(window,), daemon=True).start()


def _fire_started(window: Window) -> None:
    import webview

    # A window destroyed before it is shown never fires shown, which would hold back opened
    while not window.events.shown.wait(0.1):
        if window.events.closed.is_set():
            break

    webview.events.started.set()


def open_argv() -> None:
    """Fire webview.events.opened for the files and URLs on the command line, once per process."""
    global _argv_opened

    if _argv_opened:
        return

    _argv_opened = True
    files, urls = _parse_argv(sys.argv[1:], os.getcwd())
    if files or urls:
        fire_opened(files, urls, sys.argv[1:])


def _parse_argv(argv: list[str], cwd: str) -> tuple[list[str], list[str]]:
    """Split command line arguments into existing files and URLs, ignoring everything else."""
    files, urls = [], []

    for arg in argv:
        # Desktop entries pass files as file:// URLs with the %U field code
        if arg.startswith('file://'):
            try:
                url = urlparse(arg)
            except ValueError:
                continue

            # A host names a network share on Windows, e.g. file://server/share/document.txt
            host = '' if url.netloc in ('', 'localhost') else url.netloc
            if host and sys.platform != 'win32':
                continue

            path = url2pathname(f'//{host}{url.path}' if host else url.path)
            if os.path.isfile(path):
                files.append(os.path.abspath(path))
            continue

        path = os.path.join(cwd, arg)

        if os.path.isfile(path):
            files.append(os.path.abspath(path))
        elif _URL.match(arg):
            urls.append(arg)

    return files, urls


def fire_opened(
    files: list[str],
    urls: list[str],
    argv: list[str] | None = None,
    cwd: str | None = None,
) -> None:
    """Fire webview.events.opened, after webview.events.started. Called by the core and backends."""
    global _open_worker

    request = {'files': files, 'urls': urls, 'argv': argv or [], 'cwd': cwd or os.getcwd()}

    # A single worker fires the requests one after another, in the order they arrive
    with _open_lock:
        _open_requests.put(request)

        if _open_worker is None:
            _open_worker = threading.Thread(
                target=_fire_opened, args=(_open_requests,), name='pywebview-opened', daemon=True
            )
            _open_worker.start()


def _fire_opened(requests: queue.SimpleQueue) -> None:
    import webview

    # The queue is passed in, so that a worker of a reloaded module keeps to its own queue
    while True:
        request = requests.get()
        webview.events.started.wait()
        webview.events.opened._set_in_thread(request)


def _open_second_launch(argv: list[str], cwd: str) -> None:
    """Show the application and fire webview.events.opened for a later launch."""
    import webview

    # A launch may arrive while the first window is still starting, before a window can be active
    webview.events.started.wait()

    if webview.windows:
        try:
            window = webview.active_window() or webview.windows[0]
            # restore() also returns a maximized window to its normal size
            if window._minimized:
                window.restore()
            window.show()
        except Exception:
            # The command line is delivered even if no window can be shown
            logger.exception('Cannot show the window for a second launch of the application')

    files, urls = _parse_argv(argv, cwd)
    fire_opened(files, urls, argv, cwd)


def _key(instance_id: str | bool) -> str:
    if instance_id is True:
        instance_id = os.path.normcase(os.path.abspath(sys.argv[0]))

    try:
        user = getpass.getuser()
    except Exception:
        user = ''

    return hashlib.sha256(f'{user}:{instance_id}'.encode()).hexdigest()[:24]


def _socket_dir() -> str:
    """A directory only the current user can access, for the sockets."""
    base = os.environ.get('XDG_RUNTIME_DIR') or tempfile.gettempdir()
    directory = os.path.join(base, f'pywebview-{os.getuid()}')

    # A socket path that is too long cannot be bound, e.g. in a sandboxed app container
    if len(os.path.join(directory, '0' * 24 + '.sock').encode()) > _MAX_SOCKET_PATH:
        directory = os.path.join('/tmp', f'pywebview-{os.getuid()}')

    os.makedirs(directory, mode=0o700, exist_ok=True)

    if os.stat(directory).st_uid != os.getuid():
        raise PermissionError(f'{directory} is owned by another user')

    return directory


@contextlib.contextmanager
def _directory_lock() -> Iterator[None]:
    """
    Serialize starting and quitting instances. Held only briefly, so that the socket can be
    checked and replaced without another process doing the same at the same time.
    """
    import fcntl

    fd = os.open(_socket_dir(), os.O_RDONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def _lock_path(key: str) -> str:
    return os.path.join(_socket_dir(), f'{key}.lock')


def _try_lock(key: str) -> int | None:
    """
    Lock the file held by the running instance and return its descriptor, or return None if
    another instance holds it. Called with the directory lock held.
    """
    import fcntl

    fd = os.open(_lock_path(key), os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except BlockingIOError:
        os.close(fd)
        return None


def _listen_or_connect(key: str) -> Listener | Connection | None:
    """
def _unlock(fd: int, key: str) -> None:
    """Remove the lock file and close it. Called with the directory lock held."""
    try:
        os.unlink(_lock_path(key))
    finally:
        os.close(fd)


    Become the running instance and return its listener, or return a connection to the running
    instance. Return None if the running instance cannot be reached.
    """
    global _lock_fd, _lock_file

    if sys.platform == 'win32':
        address = rf'\\.\pipe\pywebview-{key}'

        for _ in range(_CONNECT_ATTEMPTS):
            # The first pipe instance is created with FILE_FLAG_FIRST_PIPE_INSTANCE, so this
            # fails while another instance owns the pipe
            try:
                return Listener(address, family='AF_PIPE')
            except OSError:
                pass

            # Client waits while the pipe is busy, and fails at once if the running instance
            # has just quit, in which case the pipe can be created on the next attempt
            try:
                return Client(address, family='AF_PIPE')
            except OSError:
                time.sleep(0.1)

        return None

    address = os.path.join(_socket_dir(), f'{key}.sock')

    with _directory_lock():
        fd = _try_lock(key)

        if fd is not None:
            # No instance is running, so a socket left behind by one that crashed can be removed
            try:
                if os.path.exists(address):
                    os.unlink(address)
                listener = Listener(address, family='AF_UNIX', backlog=64)
            except BaseException:
                _unlock(fd, key)
                raise

            _lock_fd, _lock_file = fd, key
            return listener

    # Another instance is running. Its socket refuses connections while its backlog is full.
    for _ in range(_CONNECT_ATTEMPTS):
        try:
            return Client(address, family='AF_UNIX')
        except FileNotFoundError:
            # The running instance has just quit
            return None
        except ConnectionRefusedError:
            time.sleep(0.1)

    return None


def release() -> None:
    """Stop being the running instance, so that later launches start their own instance."""
    global _listener, _lock_fd, _lock_file

    listener, _listener = _listener, None
    if listener is None:
        return

    if sys.platform == 'win32':
        listener.close()
        return

    fd, _lock_fd = _lock_fd, None

    # Called while quitting, also from a finally block, so it must not raise
    key, _lock_file = _lock_file, None
    try:
        # Closing the listener closes the socket and then removes the file. Without the lock, an
        # instance starting in between could replace the socket, and this would remove its socket.
        with _directory_lock():
            try:
                listener.close()
            finally:
                if fd is not None and key is not None:
                    # Every process opens the lock file with the directory lock held, so no
                    # other process has it open now
                    fd, locked = None, fd
                    _unlock(locked, key)
    except OSError:
        logger.exception('Failed to stop being the running instance of the application')
        with contextlib.suppress(OSError):
            listener.close()
    finally:
        if fd is not None:
            os.close(fd)


def _hand_over(connection: Connection) -> bool:
    """Hand the command line to the running instance."""
    message = json.dumps({'argv': sys.argv[1:], 'cwd': os.getcwd()}).encode()

    try:
        with connection:
            # A running instance that does not answer is treated as one that cannot be reached
            if not connection.poll(_HAND_OVER_TIMEOUT):
                return False

            pid = int(connection.recv_bytes(64))

            if sys.platform == 'win32':
                import ctypes

                # Only the foreground process can let another process take the foreground.
                # This process was just started by the user, so it can.
                ctypes.windll.user32.AllowSetForegroundWindow(pid)

            connection.send_bytes(message)
            return True
    except (OSError, EOFError, ValueError):
        # The running instance quit during the hand over
        return False


def _receive(connection: Connection) -> None:
    with connection:
        connection.send_bytes(str(os.getpid()).encode())

        if not connection.poll(_HAND_OVER_TIMEOUT):
            raise TimeoutError('A second launch did not send its command line')

        message = json.loads(connection.recv_bytes(_MAX_MESSAGE_SIZE))

    argv, cwd = message.get('argv'), message.get('cwd')

    if (
        not isinstance(argv, list)
        or not all(isinstance(arg, str) for arg in argv)
        or not isinstance(cwd, str)
    ):
        raise ValueError('Malformed message')

    # Launches are handled in the order their command lines arrive
    with _launch_lock:
        _open_second_launch(argv, cwd)


def _handle(connection: Connection) -> None:
    try:
        _receive(connection)
    except (EOFError, BrokenPipeError, ConnectionResetError):
        # A launch that quit before handing over
        pass
    except Exception:
        logger.exception('Failed to handle a second launch of the application')


def _serve(listener: Listener) -> None:
    while True:
        try:
            connection = listener.accept()
        except OSError:
            if _listener is listener:
                logger.exception('Single instance listener stopped')
            return

        # A launch that is slow to send its command line, and the handler, which waits on the
        # GUI, must not hold up accepting later launches
        threading.Thread(target=_handle, args=(connection,), daemon=True).start()


def claim(instance_id: str | bool) -> bool:
    """
    Make this process the single running instance of the application. Each later launch shows
    the application and fires webview.events.opened with its command line.

    :param instance_id: Identifier of the application. True derives it from the path of the
        application.
    :return: True if this process is the running instance. False if another instance is
        running, in which case the command line has been handed to it.
    """
    global _listener

    if _listener is not None:
        return True

    key = _key(instance_id)

    try:
        # The running instance may quit before it receives the command line
        for _ in range(3):
            result = _listen_or_connect(key)

            if isinstance(result, Listener):
                _listener = result
                atexit.register(release)
                threading.Thread(target=_serve, args=(result,), daemon=True).start()
                return True

            if result is not None and _hand_over(result):
                return False
    except OSError:
        logger.exception('Single instance mode is not available, starting a new instance')
        return True

    logger.warning('Another instance of the application seems to be running, but cannot be reached')
    return True


def is_running(instance_id: str | bool) -> bool:
    """
    Check whether another process is the running instance of the application.

    :param instance_id: Identifier of the application, as passed to claim().
    :return: True if another process is the running instance. False otherwise, including in
        the running instance itself.
    """
    if _listener is not None:
        return False

    key = _key(instance_id)

    try:
        if sys.platform == 'win32':
            # Create the first pipe instance and close it at once. Connecting to the running
            # instance instead would be handled as a second launch.
            try:
                Listener(rf'\\.\pipe\pywebview-{key}', family='AF_PIPE').close()
                return False
            except OSError:
                return True

        # The running instance holds the lock for its lifetime
        with _directory_lock():
            fd = _try_lock(key)
            if fd is None:
                return True
            _unlock(fd, key)
            return False
    except OSError:
        logger.exception('Cannot check for a running instance of the application')
        return False
