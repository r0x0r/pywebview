"""
CI entrypoint for the Android pytest suite.

Runs the tests symlinked into shared/ and reports results over stdout, which
python-for-android's bootstrap pipes to logcat. CI tails logcat for the
`PYWEBVIEW_TEST_RESULT::` markers rather than pulling a file off the device,
since app storage paths are more fragile than a stream CI already reads.
"""

import sys

import pytest


class LogcatReporter:
    """Prints one marker line per test result.

    One line per event, rather than an end-of-run blob, keeps each line well
    under logcat's ~4KB per-line truncation limit.
    """

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.failures = []

    @staticmethod
    def _message(report):
        """The failing assertion or exception, not the head of the long repr.

        str(longrepr) starts with the source listing and the locals, so
        truncating it cuts off before anything useful. reprcrash holds just the
        final error line.
        """
        crash = getattr(report.longrepr, 'reprcrash', None)
        text = crash.message if crash else str(report.longrepr)
        # Well inside logcat's ~4KB per-line limit, while still carrying the
        # nested traceback run_test() puts in the failure message. If the run
        # crashes, pytest never gets to print its own FAILURES section.
        return text.replace('\n', ' | ')[:1500]

    def pytest_runtest_logreport(self, report):
        if report.failed:
            # Any phase, not just call: a fixture that raises or a window that
            # will not close is a failure with no call phase to report it. One
            # line per test however many of its phases failed.
            if report.nodeid in self.failures:
                return

            self.failed += 1
            self.failures.append(report.nodeid)
            print(f'PYWEBVIEW_TEST_RESULT::FAIL::{report.nodeid}::{self._message(report)}')
        elif report.skipped:
            # Counted and reported rather than ignored: a skip silently shrinks
            # a run that is meant to execute in full.
            self.skipped += 1
            print(f'PYWEBVIEW_TEST_RESULT::SKIP::{report.nodeid}')
        elif report.when == 'call' and report.passed:
            self.passed += 1
            print(f'PYWEBVIEW_TEST_RESULT::PASS::{report.nodeid}')

    def pytest_sessionfinish(self, session, exitstatus):
        print(
            f'PYWEBVIEW_TEST_RESULT::DONE::{exitstatus}::'
            f'{self.passed}::{self.failed}::{self.skipped}'
        )


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
        'shared/test_events.py',
        'shared/test_window_android.py',
        'shared/test_request_android.py',
        'shared/test_cookies_android.py',
    ]

    print('PYWEBVIEW_TEST_RESULT::START')
    pytest.main(test_args, plugins=[reporter])

    sys.stdout.flush()
    sys.stderr.flush()
