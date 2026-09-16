"""
CI entrypoint for the Android pytest suite.

Runs the tests symlinked into shared/ and reports results over stdout, which
python-for-android's bootstrap pipes to logcat. CI tails logcat for the
`PYWEBVIEW_TEST_RESULT::` markers rather than pulling a file off the device,
since app storage paths are more fragile than a stream CI already reads.
"""

import faulthandler
import os
import sys
import threading

import pytest

# Per-test watchdog. pytest-timeout cannot be used here: it has no
# python-for-android recipe, and adding it makes p4a resolve the whole
# requirement set through pip, which cannot build proxy_tools. Without it a
# hung test stalls until CI's shell timeout with nothing naming it, and a hang
# is exactly what this suite exists to catch.
TEST_TIMEOUT = 60


class LogcatReporter:
    """Prints one marker line per test result.

    One line per event, rather than an end-of-run blob, keeps each line well
    under logcat's ~4KB per-line truncation limit.
    """

    def __init__(self):
        self.results = {}
        self.watchdog = None

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

    def pytest_runtest_logstart(self, nodeid, location):
        self.watchdog = threading.Timer(TEST_TIMEOUT, self._timed_out, (nodeid,))
        self.watchdog.daemon = True
        self.watchdog.start()

    def pytest_runtest_logfinish(self, nodeid, location):
        if self.watchdog is not None:
            self.watchdog.cancel()
            self.watchdog = None

    def _timed_out(self, nodeid):
        """Report the hung test and kill the process from the watchdog thread.

        The test is blocked, so pytest will never resume to report anything
        itself. Emitting the markers here means CI fails naming the test rather
        than timing out on a stream that stopped.
        """
        message = f'timed out after {TEST_TIMEOUT}s'
        self.results[nodeid] = {'status': 'FAIL', 'message': message}
        print(f'PYWEBVIEW_TEST_RESULT::FAIL::{nodeid}::{message}')
        faulthandler.dump_traceback(file=sys.stdout)
        self.pytest_sessionfinish(None, 1)

        sys.stdout.flush()
        sys.stderr.flush()
        # Not sys.exit(): that only raises in this thread, and the main thread
        # is the one that is stuck.
        os._exit(1)

    def pytest_runtest_logreport(self, report):
        # A test reports up to three times - setup, call, teardown - and any of
        # them can fail. Fold them into one outcome and print it at teardown,
        # so a test that passes and then fails to tear down is not counted
        # twice, and a failed setup is not also reported as a skipped call.
        result = self.results.setdefault(report.nodeid, {'status': None, 'message': ''})

        if report.failed:
            # Failure wins over an earlier pass, but the first failure's message
            # is the one that explains the run.
            if result['status'] != 'FAIL':
                result['status'] = 'FAIL'
                result['message'] = self._message(report)
        elif result['status'] is None:
            if report.skipped:
                # Recorded rather than ignored: a skip silently shrinks a run
                # that is meant to execute in full.
                result['status'] = 'SKIP'
            elif report.when == 'call' and report.passed:
                result['status'] = 'PASS'

        if report.when != 'teardown':
            return

        status = result['status'] or 'SKIP'
        line = f'PYWEBVIEW_TEST_RESULT::{status}::{report.nodeid}'
        print(f'{line}::{result["message"]}' if status == 'FAIL' else line)

    def pytest_sessionfinish(self, session, exitstatus):
        counts = {'PASS': 0, 'FAIL': 0, 'SKIP': 0}

        for result in self.results.values():
            counts[result['status'] or 'SKIP'] += 1

        print(
            f'PYWEBVIEW_TEST_RESULT::DONE::{exitstatus}::'
            f'{counts["PASS"]}::{counts["FAIL"]}::{counts["SKIP"]}'
        )


if __name__ == '__main__':
    reporter = LogcatReporter()

    test_args = [
        '-p',
        'no:cacheprovider',
        '-v',
        # Capture off: the watchdog prints from another thread while a test is
        # still running, and captured output is discarded when it kills the
        # process. Everything here goes to logcat regardless.
        '-s',
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
