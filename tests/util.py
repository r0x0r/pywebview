import threading
import time
import json
import os
import sys
import logging
import traceback
import pytest
from uuid import uuid4
from multiprocessing import Process, Queue

logger = logging.getLogger('pywebview')


def run_test(webview, window, thread_func=None, param=None, start_args={}, no_destroy=False, destroy_delay=0):
    __tracebackhide__ = True
    try:
        queue = Queue()

        time.sleep(2)
        _create_window(webview, window, thread_func, queue, param, start_args, no_destroy, destroy_delay)

        if not queue.empty():
            e = queue.get()
            pytest.fail(e)

    except Exception as e:
        pytest.fail(e)


def assert_js(window, func_name, expected_result, *func_args):
    value_id = 'v' + uuid4().hex[:8]
    func_args = str(func_args).replace(',)', ')')

    execute_func = """
    window.pywebview.api.{0}{1}.then(function(value) {{
        window.{2} = value
    }}).catch(function() {{
        window.{2} = 'error'
    }})
    """.format(func_name, func_args, value_id)
    check_func = 'window.{0}'.format(value_id)

    window.evaluate_js(execute_func)

    result = window.evaluate_js(check_func)
    counter, MAX = 0, 50

    while result is None:
        if counter == MAX:
            raise AssertionError('assert_js timeout')
        else:
            counter += 1
            time.sleep(0.1)
            result = window.evaluate_js(check_func)

    assert expected_result == result


def _create_window(webview, window, thread_func, queue, thread_param, start_args, no_destroy, destroy_delay):

    def thread():
        try:
            if thread_func:
                thread_func(window)

            destroy_event.set()
        except Exception as e:
            logger.exception(e, exc_info=True)
            queue.put(traceback.format_exc())
            destroy_event.set()

    if not no_destroy:
        args = (thread_param,) if thread_param else ()
        destroy_event = _destroy_window(webview, window, destroy_delay)

        t = threading.Thread(target=thread, args=args)
        t.start()

    webview.start(**start_args)


def get_test_name():
    return os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0]


def _destroy_window(webview, window, delay):
    def stop():
        event.wait()
        time.sleep(delay)
        window.destroy()

        if sys.platform == 'darwin':
            from .util_cocoa import mouseMoveRelative
            time.sleep(1)
            mouseMoveRelative(1, 1)

    event = threading.Event()
    event.clear()
    t = threading.Thread(target=stop)
    t.start()

    return event


