import os
import socket
import subprocess
import sys
import time

import pytest

import webview
from webview import instance

from .util import run_test

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LAUNCH = """
import os
import webview

webview.create_window('Second instance', html='<html><body>Second</body></html>')
webview.start(single_instance=os.environ['PYWEBVIEW_INSTANCE_ID'])
"""

CHECK = """
import os
import webview

print(webview.is_instance_running(os.environ['PYWEBVIEW_INSTANCE_ID']))
"""

CLAIM = """
import os
from webview import instance

assert instance.claim(os.environ['PYWEBVIEW_INSTANCE_ID'])
assert instance._listener is not None
"""


@pytest.mark.skipif(sys.platform == 'win32', reason='Named pipes leave no files behind')
def test_stale_socket(tmp_path):
    instance_id = 'pywebview-test-stale'
    address = os.path.join(instance._socket_dir(), f'{instance._key(instance_id)}.sock')

    # A socket left behind by an instance that crashed
    stale = socket.socket(socket.AF_UNIX)
    stale.bind(address)
    stale.close()

    run(instance_id, tmp_path, CLAIM)
    assert not os.path.exists(address)


def test_second_launch(monkeypatch, tmp_path):
    # The running instance's own command line opens nothing
    monkeypatch.setattr('sys.argv', ['app'])
    (tmp_path / 'document.txt').write_text('test')
    instance_id = 'pywebview-test'

    assert not webview.is_instance_running(instance_id)

    window = webview.create_window('Single instance test', html='<html><body>TEST</body></html>')
    received = []
    webview.events.opened += lambda request: received.append(request['files'])

    run_test(
        webview,
        window,
        second_launch,
        (instance_id, tmp_path, received),
        start_args={'single_instance': instance_id},
    )


def second_launch(window, instance_id, cwd, received):
    # Another process sees the running instance, the running instance does not see itself
    assert not webview.is_instance_running(instance_id)
    assert run(instance_id, cwd, CHECK).stdout.strip() == 'True'

    # Every launch fires opened, with the arguments that are existing files
    launch(instance_id, cwd)
    launch(instance_id, cwd, 'document.txt', 'missing.txt')

    for _ in range(50):
        if len(received) == 2:
            break
        time.sleep(0.1)

    # Launches are handled in the order they arrive
    assert received == [[], [os.path.realpath(cwd / 'document.txt')]], received


def launch(instance_id, cwd, *args):
    # A launch that fails to hand over opens a window of its own and runs into the timeout
    run(instance_id, cwd, LAUNCH, *args)


def run(instance_id, cwd, script, *args):
    env = {**os.environ, 'PYTHONPATH': ROOT, 'PYWEBVIEW_INSTANCE_ID': instance_id}
    result = subprocess.run(
        [sys.executable, '-c', script, *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return result
