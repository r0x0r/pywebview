import os
from importlib import reload

import pytest

# Path to append each test's outcome to, or None to record nothing. Set by
# tests/run.ps1 for the WinUI3 backend; unset everywhere else, where pytest's
# own exit code is already trustworthy.
_OUTCOME_LOG = os.environ.get('PYWEBVIEW_TEST_OUTCOME_LOG')


def pytest_runtest_logreport(report):
    """
    Append each test's outcome to `PYWEBVIEW_TEST_OUTCOME_LOG` as soon as it is
    known, rather than leaving the record to pytest's end-of-session summary.

    WinUI3 needs this. `Application.current.exit()` in winui3.py's
    last-window-close teardown tears the whole process down once a test has
    opened and closed a window -- before pytest prints its summary or sets an
    exit code. A failing test would otherwise leave nothing behind but a bare
    `F` in the log and an exit status of 0, so the runner would call the job
    green. Writing and flushing per report survives that teardown.
    """
    if not _OUTCOME_LOG:
        return

    # The call phase is the test itself; setup/teardown only matter when they
    # did not pass (a collection error, a skip, a failing fixture).
    if report.when != 'call' and report.outcome == 'passed':
        return

    with open(_OUTCOME_LOG, 'a', encoding='utf-8') as f:
        f.write(f'{report.outcome}\t{report.when}\t{report.nodeid}\n')
        f.flush()


@pytest.fixture(autouse=True)
def reload_webview():
    import webview
    from webview import http

    reload(webview)
    reload(http)


@pytest.fixture(autouse=True)
def set_env():
    os.environ['PYWEBVIEW_TEST'] = 'true'


# @pytest.fixture(autouse=True)
# def set_gui():
#     import os
#     os.environ['PYWEBVIEW_GUI'] = 'qt'
