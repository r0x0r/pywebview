"""
CI entrypoint for the Android pytest suite.

Unlike tests/android/main.py (the manual, on-screen Mocha harness), this app
runs the real pytest suite reused from tests/ (symlinked into shared/) headlessly
and reports results over stdout, which python-for-android's bootstrap pipes to
logcat. CI tails logcat for the `PYWEBVIEW_TEST_RESULT::` markers below instead
of pulling a file off the device, since app storage permissions/paths are more
fragile to depend on than a stream CI already has to read anyway.

Each shared test module creates and destroys its own window per test via
tests/util.py's run_test()/create_test_window(), so this entrypoint does not
own a window itself - it only drives pytest and prints markers.
"""

import sys

import pytest


class LogcatReporter:
    """Minimal pytest plugin that prints one marker line per test result.

    One line per event (rather than a single end-of-run JSON blob) keeps each
    line well under logcat's ~4KB per-line truncation limit even if a failure
    message is long.
    """

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.failures = []

    @staticmethod
    def _message(report):
        """The failing assertion or exception, not the head of the long repr.

        str(longrepr) starts with the source listing and the local variables,
        so truncating it to fit a logcat line reliably cuts off before reaching
        anything about what actually went wrong. reprcrash holds just the final
        error line.
        """
        crash = getattr(report.longrepr, 'reprcrash', None)
        text = crash.message if crash else str(report.longrepr)
        return text.replace('\n', ' | ')[:300]

    def pytest_runtest_logreport(self, report):
        if report.when != 'call' and not (report.when == 'setup' and report.failed):
            return

        if report.failed:
            self.failed += 1
            self.failures.append(report.nodeid)
            print(f'PYWEBVIEW_TEST_RESULT::FAIL::{report.nodeid}::{self._message(report)}')
        elif report.passed:
            self.passed += 1
            print(f'PYWEBVIEW_TEST_RESULT::PASS::{report.nodeid}')

    def pytest_sessionfinish(self, session, exitstatus):
        print(f'PYWEBVIEW_TEST_RESULT::DONE::{exitstatus}::{self.passed}::{self.failed}')


if __name__ == '__main__':
    reporter = LogcatReporter()

    test_args = [
        '-p',
        'no:cacheprovider',
        '-v',
        '--rootdir',
        '.',
        'shared/test_state.py',
        'shared/test_evaluate_js.py',
        'shared/test_js_api.py',
        'shared/test_dom.py',
        'shared/test_cookies_android.py',
    ]

    print('PYWEBVIEW_TEST_RESULT::START')
    pytest.main(test_args, plugins=[reporter])

    sys.stdout.flush()
    sys.stderr.flush()
