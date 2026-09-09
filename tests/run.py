import os
import sys

import pytest

if __name__ == '__main__':
    exit_code = pytest.main(['-s'])
    # Flush and force-exit to avoid hanging on lingering non-daemon threads that
    # GUI backends may keep alive after the test session has finished. Without
    # this, interpreter shutdown blocks on joining those threads and the CI job
    # times out even though all tests have passed.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(int(exit_code))
