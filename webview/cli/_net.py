from __future__ import annotations

import socket
import time
import urllib.error
import urllib.request


def pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def wait_for_url(url: str, timeout: float = 30.0, interval: float = 0.3) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=interval)
            return True
        except urllib.error.URLError:
            time.sleep(interval)
        except (ConnectionError, OSError):
            time.sleep(interval)
    return False
