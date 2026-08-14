import os
import subprocess
import sys
import time

import pytest

PRIMARY_SCRIPT = """
import sys, time
from webview.single_instance import enforce_single_instance

received = []
def on_second(argv):
    with open(sys.argv[1], 'a') as f:
        f.write(repr(argv) + chr(10))

is_primary = enforce_single_instance(on_second_instance=on_second, identifier=sys.argv[2])
print('PRIMARY' if is_primary else 'SECONDARY', flush=True)
if is_primary:
    time.sleep(float(sys.argv[3]))
"""

SECOND_SCRIPT = """
import sys
from webview.single_instance import enforce_single_instance

is_primary = enforce_single_instance(identifier=sys.argv[1])
print('PRIMARY' if is_primary else 'SECONDARY', flush=True)
"""


@pytest.fixture
def scripts(tmp_path):
    primary_path = tmp_path / 'primary.py'
    second_path = tmp_path / 'second.py'
    primary_path.write_text(PRIMARY_SCRIPT)
    second_path.write_text(SECOND_SCRIPT)
    return str(primary_path), str(second_path)


class TestSingleInstance:
    def test_second_launch_detected_and_forwards_argv(self, scripts, tmp_path):
        primary_path, second_path = scripts
        identifier = f'pytest-si-{os.getpid()}'
        received_file = tmp_path / 'received.txt'

        primary_proc = subprocess.Popen(
            [sys.executable, primary_path, str(received_file), identifier, '2.5'],
            stdout=subprocess.PIPE,
            text=True,
        )
        time.sleep(0.6)

        second1 = subprocess.run(
            [sys.executable, second_path, identifier], capture_output=True, text=True
        )
        second2 = subprocess.run(
            [sys.executable, second_path, identifier], capture_output=True, text=True
        )

        assert second1.stdout.strip() == 'SECONDARY'
        assert second2.stdout.strip() == 'SECONDARY'

        primary_stdout, _ = primary_proc.communicate(timeout=5)
        assert primary_stdout.strip() == 'PRIMARY'

        assert received_file.exists()
        lines = received_file.read_text().splitlines()
        assert len(lines) == 2

    def test_first_launch_alone_is_primary(self, scripts):
        _primary_path, second_path = scripts
        identifier = f'pytest-si-solo-{os.getpid()}'

        result = subprocess.run(
            [sys.executable, second_path, identifier], capture_output=True, text=True, timeout=5
        )
        assert result.stdout.strip() == 'PRIMARY'

    def test_recovers_from_stale_socket_file(self, scripts, tmp_path):
        primary_path, second_path = scripts
        identifier = f'pytest-si-stale-{os.getpid()}'
        received_file = tmp_path / 'received.txt'

        proc = subprocess.Popen(
            [sys.executable, primary_path, str(received_file), identifier, '10'],
            stdout=subprocess.PIPE,
            text=True,
        )
        time.sleep(0.6)
        proc.kill()  # simulate a crash, leaving a stale socket file behind
        proc.wait(timeout=5)
        time.sleep(0.2)

        result = subprocess.run(
            [sys.executable, second_path, identifier], capture_output=True, text=True, timeout=5
        )
        assert result.stdout.strip() == 'PRIMARY'
